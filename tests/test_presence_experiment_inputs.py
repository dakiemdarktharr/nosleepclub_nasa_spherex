"""Synthetic geometry and generator contracts; no telescope data or random draws."""
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import astropy.units as u
import numpy as np

from scripts import presence_experiment_inputs as inputs


def geometry():
    return [{'obs_id': f'f{i}', 'frame': {'image_header': {}, 'record': {'obs_id': f'f{i}', 'epoch': '2025-11' if i < 2 else '2026-04'}},
             'x': np.arange(4), 'y': np.arange(4), 'omega': np.ones(4) * u.sr,
             'gain': np.ones(4) * inputs.control.GAIN, 'error': np.full(4, 2. + i),
             'background': np.column_stack([np.ones(4), np.arange(4), np.arange(4) ** 2]),
             'neighbors': [{'native_xy': [1., 1.]}]} for i in range(4)]


def scene_context():
    geos = geometry()
    scenarios = [{'frames': [{'obs_id': geo['obs_id'], 'expected_source_mjysr': [s + 1.] * 4,
                              'background_mjysr': [0.] * 4} for geo in geos]}
                 for s in range(6)]
    return {'geometries': geos, 'scenarios': scenarios}


class PresenceInputsTests(unittest.TestCase):
    def test_grid_441_order_and_boundaries(self):
        grid = inputs.grid()
        self.assertEqual(grid.shape, (441, 2))
        np.testing.assert_allclose(grid[0], [29., 29.])
        np.testing.assert_allclose(grid[20], [34., 29.])
        np.testing.assert_allclose(grid[21], [29., 29.25])
        np.testing.assert_allclose(grid[220], [31.5, 31.5])
        np.testing.assert_allclose(grid[-1], [34., 34.])
        self.assertEqual(len({tuple(row) for row in grid}), 441)

    def test_truth_null_has_only_positive_neighbors_and_positive_has_target(self):
        seen = []
        def expected(sources, x, y, omega):
            seen.append(sources)
            return {'expected_source': np.ones(len(x)) * inputs.I, 'per_source': []}
        with patch.object(inputs.control, 'expected_scene', side_effect=expected), \
             patch.object(inputs.prior.inputs, 'native_position', side_effect=lambda frame, sky: np.asarray(sky)):
            null = inputs.truth_scenario(geometry(), inputs.SCENARIOS[0])
            positive = inputs.truth_scenario(geometry(), inputs.SCENARIOS[3])
        self.assertEqual([len(x) for x in seen], [1] * 4 + [2] * 4)
        self.assertTrue(all(source['flux'] > 0 * u.Jy for group in seen for source in group))
        self.assertEqual(seen[4][0]['flux'].to_value(u.Jy), .0006)
        np.testing.assert_allclose(seen[4][0]['native_xy'], [31.73, 31.31])
        np.testing.assert_allclose(seen[6][0]['native_xy'], [32.28, 31.39])
        self.assertEqual([f['obs_id'] for f in null['frames']], ['f0', 'f1', 'f2', 'f3'])
        self.assertEqual(positive['scenario']['id'], 'plane_600uJy')

    def test_seed_stages_scenarios_frames_unique_without_drawing_noise(self):
        ctx = scene_context(); calls = []
        def draw(source, background, error, gain, header, rng, *, gain_provenance, source_provenance):
            calls.append((source.value.copy(), error.value.copy(), source_provenance['seed']))
            return {'data': source + background, 'error': np.ones(4) * 1e9 * inputs.I,
                    'provenance': {'fake': True}}
        with patch.object(inputs.control, 'draw_scene', side_effect=draw):
            results = [inputs.realize(ctx, stage, scenario, draw_id)
                       for stage, scenario, draw_id in [('calibration', 0, 0), ('validation', 0, 0),
                                                         ('validation', 1, 0), ('validation', 2, 0),
                                                         ('validation', 2, 1)]]
        seeds = [tuple(frame['seed']) for _, meta in results for frame in meta['frames']]
        self.assertEqual(len(seeds), 20); self.assertEqual(len(set(seeds)), 20)
        self.assertEqual(seeds[:4], [(20261101, 0, 0, 0, 0, 0), (20261101, 0, 0, 0, 0, 1),
                                    (20261101, 0, 0, 0, 1, 0), (20261101, 0, 0, 0, 1, 1)])
        self.assertTrue(all(np.all(error == 2. + index % 4) for index, (_, error, _) in enumerate(calls)))
        self.assertEqual(len({meta['realization_sha256'] for _, meta in results}), 3)
        with self.assertRaises(ValueError):
            inputs.realize(ctx, 'calibration', 2, 0)

    def test_realize_rejects_misordered_or_missing_scenario_frames_before_generator(self):
        ctx = scene_context()
        ctx['scenarios'][0]['frames'][0], ctx['scenarios'][0]['frames'][1] = ctx['scenarios'][0]['frames'][1], ctx['scenarios'][0]['frames'][0]
        with patch.object(inputs.control, 'draw_scene') as draw:
            with self.assertRaises(ValueError): inputs.realize(ctx, 'calibration', 0, 0)
            draw.assert_not_called()
        for order in ([2, 3, 0, 1], [0, 2, 1, 3]):
            ctx = scene_context()
            ctx['geometries'] = [ctx['geometries'][i] for i in order]
            for scenario in ctx['scenarios']:
                scenario['frames'] = [scenario['frames'][i] for i in order]
            with self.subTest(order=order), patch.object(inputs.control, 'draw_scene') as draw:
                with self.assertRaisesRegex(ValueError, 'two before'):
                    inputs.realize(ctx, 'calibration', 0, 0)
                draw.assert_not_called()
        ctx = scene_context();ctx['scenarios'][0]['frames'].pop()
        with patch.object(inputs.control, 'draw_scene') as draw:
            with self.assertRaises(ValueError): inputs.realize(ctx, 'calibration', 0, 0)
            draw.assert_not_called()

    def test_paired_operators_receive_same_realization_and_not_oracle_error(self):
        seen = []
        class FakeOperator:
            def __init__(self, frame, variant): self.frame, self.variant = frame, variant
            def score(self, data):
                seen.append((self.frame, self.variant, data.to_value(inputs.I).copy()))
                return np.full(441, self.frame + 1.)
        ctx = {'operators': [[{'operator': FakeOperator(i, v)} for v in range(2)] for i in range(4)]}
        data = [np.full(4, i + .5) for i in range(4)]
        result = inputs.score_data(ctx, data)
        self.assertEqual(len(seen), 8)
        for frame in range(4):
            a = next(x for x in seen if x[:2] == (frame, 0))
            b = next(x for x in seen if x[:2] == (frame, 1))
            np.testing.assert_array_equal(a[2], b[2])
            np.testing.assert_array_equal(a[2], data[frame])
        self.assertEqual(result['combined'], 5.)
        self.assertEqual(len(result['winners']), 4)

    def test_build_uses_original_per_frame_errors_and_checks_arm_identity(self):
        geos = geometry()
        prepared = [[{'obs_id': f'f{i}', 'error': geos[i]['error'], 'data': np.ones(4),
                      'sample': {'x': geos[i]['x'], 'y': geos[i]['y'], 'neighbour_ids': ['n']}}
                     for i in range(e*2,e*2+2)] for e in range(2)]
        groups = [[g['frame'] for g in geos[:2]], [g['frame'] for g in geos[2:]]]
        seen = []
        def semantic(items, anchor, *, background_order, epsf_kind):
            result = []
            for item in items:
                i = int(item['obs_id'][1:])
                result.append({**item, 'background_design': geos[i]['background'],
                    'neighbor_design': np.ones((4, 1)), 'neighbor_ids': ['n'],
                    'renderer': lambda p: np.array([p[0], p[1], 1., 2.]) * inputs.I / u.Jy,
                    'metadata': {'variant': epsf_kind, 'x': geos[i]['x'], 'y': geos[i]['y']}})
            return result
        def operator(templates, error, nuisance, *, provenance):
            seen.append((provenance, error.to_value(inputs.I).copy(), templates.shape))
            return SimpleNamespace(_directions=np.zeros((441, 4)), projected_template_norm=np.ones(441) / u.Jy,
                                   information_fraction=np.ones(441), nuisance_rank=4, nuisance_condition=1.)
        def control_geo(old, sem, gain):
            return [geos[int(item['obs_id'][1:])] for item in old]
        with patch.object(inputs.prior.inputs, 'read_verified_frames', return_value=([], {})), \
             patch.object(inputs.prior, 'prepare_configuration', return_value=(groups, prepared, [None, None])), \
             patch.object(inputs.prior, 'load_gain', return_value=None), \
             patch.object(inputs.prior, 'control_geometry', side_effect=control_geo), \
             patch.object(inputs.semantic, 'prepare_semantic', side_effect=semantic), \
             patch.object(inputs.presence, 'prepare_operator', side_effect=operator), \
             patch.object(inputs, 'truth_scenario', side_effect=lambda g, s: {'scenario': s, 'frames': []}):
            result = inputs.build_geometry()
        self.assertEqual(len(result['operators']), 4)
        self.assertEqual(len(seen), 8)
        for label, error, shape in seen:
            i = int(label[1]);np.testing.assert_array_equal(error, geos[i]['error'])
            self.assertEqual(shape, (441, 4))
        self.assertEqual([f['obs_id'] for f in result['snapshot']['frames']], ['f0', 'f1', 'f2', 'f3'])

    def test_prepared_pair_refuses_changed_pixel_error_identity_or_neighbors(self):
        original = {'obs_id': 'a', 'data': np.array([1., 2.]), 'error': np.array([3., 4.]),
                    'sample': {'x': np.array([0, 1]), 'y': np.array([1, 2]), 'neighbour_ids': ['n']}}
        item = {'obs_id': 'a', 'data': original['data'].copy(), 'error': original['error'].copy(),
                'metadata': {'x': [0, 1], 'y': [1, 2]}, 'neighbor_ids': ['n']}
        inputs.validate_prepared_pair(original, item)
        bad = [dict(item, obs_id='b'), dict(item, data=np.array([2., 1.])),
               dict(item, error=np.array([3., 9.])), dict(item, metadata={'x': [1, 0], 'y': [1, 2]}),
               dict(item, neighbor_ids=['other'])]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(ValueError):
                inputs.validate_prepared_pair(original, value)


if __name__ == '__main__':
    unittest.main()
