"""Synthetic replay tests; no journal, real observations, fits or random draws."""
import copy
import gzip
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import astropy.units as u
import numpy as np
from scipy.stats import beta

from scripts import publish_presence_study as pub
from scripts import run_wise_linked_study as legacy


ROOT = Path(__file__).resolve().parents[1]


class PresencePublicationTests(unittest.TestCase):
    def test_qr_projection_matches_joint_weighted_least_squares(self):
        templates = np.array([[1., .2, .3, 2., .1], [.1, .5, 1., .2, .9]])
        nuisance = np.column_stack([np.ones(5), [0., 1., 2., 3., 4.]])
        error = np.array([1., .5, 2., 1.5, .8])
        y = np.array([2., -1., 3., .2, 2.])
        result = pub.qr_operator(templates, error, nuisance)
        for i, p in enumerate(templates):
            design = np.column_stack([nuisance, p]) / error[:, None]
            coeff = np.linalg.lstsq(design, y/error, rcond=None)[0][-1]
            information = 1. / np.linalg.inv(design.T @ design)[-1, -1]
            self.assertAlmostEqual(result['directions'][i] @ (y/error), coeff * np.sqrt(information), places=11)
            self.assertAlmostEqual(result['norm'][i], np.sqrt(information), places=11)
            self.assertAlmostEqual(result['fraction'][i], information / ((p/error) @ (p/error)), places=11)
        with self.assertRaisesRegex(ValueError, 'rank deficient'):
            pub.qr_operator(templates, error, np.column_stack([np.ones(5), np.ones(5)]))

    def test_geometry_reconstruction_rejects_template_and_column_tamper(self):
        inp = pub.inputs; grid = inp.grid();x = np.arange(8)
        background = np.column_stack([np.ones(8), x, x*x])
        neighbor = np.array([0., 0., 0., 1., 0., 0., 0., 0.])[:, None]
        raw = []; groups = []; geos = []
        def renderer(pos):
            return (np.exp(-.5*(x-pos[0]/5.)**2) + pos[1]*.001*x**3) * inp.I / u.Jy
        for epoch in range(2):
            group = [];prepared = []
            for i in range(epoch*2, epoch*2+2):
                frame = {'record': {'obs_id': f'f{i}', 'epoch': inp.RULES['frame_epoch_order'][i]}}
                item = {'obs_id': f'f{i}', 'data': np.full(8, i), 'error': np.full(8, i+1.),
                        'sample': {'x': x, 'y': x, 'neighbour_ids': ['n']}}
                geo = {'obs_id': f'f{i}', 'frame': frame, 'x': x, 'y': x,
                       'omega': np.ones(8)*u.sr, 'gain': np.ones(8)*inp.control.GAIN,
                       'error': item['error']}
                group.append(frame);prepared.append(item);geos.append(geo)
            groups.append(group);raw.append(prepared)
        def semantic(items, anchor, *, background_order, epsf_kind):
            return [{**item, 'renderer': renderer, 'background_design': background,
                     'neighbor_design': neighbor, 'neighbor_ids': ['n'],
                     'metadata': {'x': x.tolist(), 'y': x.tolist(), 'variant': epsf_kind}} for item in items]
        template = np.array([renderer(p).to_value(inp.I/u.Jy) for p in grid])
        snapshot_frames = []
        for i, geo in enumerate(geos):
            variants = []
            for variant in inp.VARIANTS:
                op = inp.presence.prepare_operator(template * inp.I/u.Jy, geo['error']*inp.I,
                     [background[:, j]*inp.I for j in range(3)] + [neighbor[:, 0]*inp.I/u.Jy], provenance='test')
                variants.append({'variant': variant, 'metadata': {'x': x.tolist(), 'y': x.tolist(), 'variant': variant},
                    'background_design': background.tolist(), 'neighbor_design_per_jy': neighbor.tolist(),
                    'neighbor_ids': ['n'], 'templates_sha256': sha256(legacy.encoded(template)).hexdigest(),
                    'projected_directions': op._directions.tolist(), 'projected_norm_per_jy': op.projected_template_norm.value.tolist(),
                    'information_fraction': op.information_fraction.tolist(), 'nuisance_rank': op.nuisance_rank,
                    'nuisance_condition': op.nuisance_condition})
            snapshot_frames.append({'obs_id': geo['obs_id'], 'x': x.tolist(), 'y': x.tolist(),
                'pixel_omega_sr': [1.]*8, 'gain_mjysr_per_electron_rate': [1.]*8,
                'observed_error_mjysr': geo['error'].tolist(), 'variants': variants})
        snapshot = {'rules': inp.RULES, 'grid_sky_px': grid.tolist(), 'frames': snapshot_frames,
                    'observed_data_sha256': sha256(legacy.encoded([item['data'] for group in raw for item in group])).hexdigest(),
                    'truth_scenarios': [{'scenario': scenario} for scenario in inp.SCENARIOS]}
        def control_geo(old, semantic_items, gain):
            return [geos[int(item['obs_id'][1:])] for item in old]
        with patch.object(inp.prior.inputs, 'read_verified_frames', return_value=([], {})), \
             patch.object(inp.prior, 'prepare_configuration', return_value=(groups, raw, [None, None])), \
             patch.object(inp.prior, 'load_gain', return_value=None), \
             patch.object(inp.prior, 'control_geometry', side_effect=control_geo), \
             patch.object(inp.semantic, 'prepare_semantic', side_effect=semantic), \
             patch.object(inp, 'truth_scenario', side_effect=lambda g, s: {'scenario': s}):
            self.assertEqual(len(pub.replay_geometry(snapshot)), 4)
            for field in ('templates_sha256', 'background_design', 'projected_directions'):
                altered = copy.deepcopy(snapshot)
                variant = altered['frames'][0]['variants'][0]
                if field == 'templates_sha256': variant[field] = 'bad'
                else: variant[field][0][0] += .5
                with self.subTest(field=field), self.assertRaises(ValueError):
                    pub.replay_geometry(altered)

    def test_independent_score_one_sided_and_exact_winners(self):
        ops = [[{'directions': np.eye(2), 'error': np.ones(2)} for _ in range(2)] for _ in range(4)]
        grid = [[10., 10.], [11., 10.]]
        score = pub.independent_score([[1., -8.], [2., 3.], [0., 1.], [-1., 2.]], ops, grid)
        self.assertEqual(score['before'], [9., 9.]);self.assertEqual(score['after'], [5., 5.])
        self.assertEqual(score['combined'], 5.)
        self.assertEqual([winner['grid_index'] for winner in score['winners']], [1, 1, 1, 1])
        self.assertEqual(score['winners'][0]['signed_frame_scores'], [-8., 3.])

    def fixture_record(self):
        grid = [[0., 0.], [1., 0.]]
        operators = [[{'directions': np.eye(2), 'error': np.ones(2)} for _ in range(2)] for _ in range(4)]
        data = [[1., -8.], [2., 3.], [0., 1.], [-1., 2.]]
        snapshot = {'grid_sky_px': grid, 'frames': [], 'truth_scenarios': []}
        for i in range(4): snapshot['frames'].append({'obs_id': f'f{i}', 'observed_error_mjysr': [1., 1.],
                                                      'gain_mjysr_per_electron_rate': [1., 1.]})
        for scenario in pub.inputs.SCENARIOS:
            snapshot['truth_scenarios'].append({'scenario': scenario,
                'frames': [{'obs_id': f'f{i}', 'background_mjysr': [0., 0.],
                            'expected_source_mjysr': [2., 2.]} for i in range(4)]})
        frames = []
        for i in range(4):
            seed = [pub.inputs.RULES['seed_prefix'], 1, 2, 0, i//2, i%2]
            source = {'scenario': 'plane_300uJy', 'seed': seed,
                      'source': 'fixed independent Gaussian-family conditional presence scene'}
            gain = {'source': pub.inputs.prior.gain_paths.URL,
                    'sha256': pub.inputs.prior.gain_binding.GAIN_SHA256,
                    'orientation': 'conditional public R6 binding'}
            frames.append({'obs_id': f'f{i}', 'seed': seed, 'data_mjysr': data[i],
                'provenance': {'source_provenance': source, 'gain_provenance': gain, 'rng_state_before': {'mock': 1},
                               'source_ramp': {'gain_provenance': gain, 'source_provenance': source,
                                   'source_values_sha256': pub._array_hash([[2., 2.]]),
                                   'gain_values_sha256': pub._array_hash([[1., 1.]]),
                                   'valid_mask_sha256': sha256(b'(1, 2)|' + bytes([1, 1])).hexdigest(),
                                   'valid_pixels': 2, 'shape': [1, 2],
                                   'rng_bit_generator': 'PCG64', 'rng_state_before': {'mock': 1}},
                               'rng_bit_generator': 'PCG64', 'pixels': 2,
                               'background_values_sha256': pub._array_hash([0., 0.]),
                               'background_error_values_sha256': pub._array_hash([1., 1.])}})
        row = {'key': ['validation', 'plane_300uJy', '0'], 'payload': {
            'status': 'score_completed', 'scenario': pub.inputs.SCENARIOS[2], 'scenario_index': 2, 'draw': 0,
            'realization': {'frames': frames, 'realization_sha256': sha256(legacy.encoded(data)).hexdigest()},
            'score': pub.independent_score(data, operators, grid), 'accepted': False}}
        return row, snapshot, operators

    def test_record_replay_refuses_tampering_and_threshold_tie(self):
        row, snapshot, operators = self.fixture_record()
        pub.audit_record(row, snapshot, operators, 5.)
        for mutation in ('data', 'seed', 'background', 'score', 'accepted', 'scenario'):
            value = copy.deepcopy(row)
            if mutation == 'data': value['payload']['realization']['frames'][0]['data_mjysr'][0] += 1
            if mutation == 'seed': value['payload']['realization']['frames'][0]['seed'][0] += 1
            if mutation == 'background': value['payload']['realization']['frames'][0]['provenance']['background_values_sha256'] = 'bad'
            if mutation == 'score': value['payload']['score']['combined'] = 9
            if mutation == 'accepted': value['payload']['accepted'] = True
            if mutation == 'scenario': value['payload']['scenario_index'] = 3
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                pub.audit_record(value, snapshot, operators, 5.)

    def test_failed_null_is_false_accept_and_failed_positive_miss(self):
        rows = []
        for scenario in pub.inputs.SCENARIOS:
            for draw in range(3):
                payload = {'status': 'score_failed', 'error': 'failure'} if draw == 2 else {
                    'status': 'score_completed', 'accepted': draw == 0}
                rows.append({'key': ['validation', scenario['id'], str(draw)], 'payload': payload})
        with patch.dict(pub.inputs.RULES, {'draws_per_case': 3}):
            results = pub.case_summaries(rows, 5.)
        self.assertEqual(len(results), 6)
        null, positive = results[0], results[2]
        self.assertEqual((null['planned'], null['completed'], null['failed'], null['accepted']), (3, 2, 1, 1))
        self.assertEqual(null['conservative_events'], 2)
        self.assertAlmostEqual(null['false_accept_upper'], beta.ppf(.975, 3, 1))
        self.assertEqual(positive['conservative_events'], 1)
        self.assertAlmostEqual(positive['power_lower'], beta.ppf(.025, 1, 3))
        self.assertIsNone(positive['gate_pass'])
        self.assertIsNone(null['power_lower'])

    def test_gzip_is_deterministic_and_hashes_match(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            path = Path(temp)
            overview = {'schema': 'source-presence-overview-1', 'promotion': False}
            full = {'overview': overview, 'geometry': {'fixed': [1, 2]}, 'records': []}
            first = pub.publish(overview, full, path)
            packed = (path/'records.json.gz').read_bytes()
            self.assertEqual(sha256(packed).hexdigest(), first['download']['sha256'])
            self.assertEqual(sha256(gzip.decompress(packed)).hexdigest(), first['download']['uncompressed_sha256'])
            self.assertEqual(json.loads(gzip.decompress(packed)), full)
            second = pub.publish(overview, full, path)
            self.assertEqual(first, second)
            self.assertEqual(packed, (path/'records.json.gz').read_bytes())

    def test_incomplete_artifacts_never_create_journals(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temp, \
             patch.object(pub.study, 'OUTPUT', Path(temp)/'absent'), \
             patch.object(pub.study, 'GEOMETRY', Path(temp)/'absent'/'geometry.json'), \
             patch.object(pub.study, 'THRESHOLD', Path(temp)/'missing.json'), \
             patch.object(pub.study.frozen, 'verify'):
            with patch.object(pub.study, 'open_journal') as opening:
                with self.assertRaisesRegex(ValueError, 'artifact missing'):
                    pub.build('a'*40, 'b'*40)
                opening.assert_not_called()
                self.assertFalse((Path(temp)/'absent').exists())


if __name__ == '__main__': unittest.main()
