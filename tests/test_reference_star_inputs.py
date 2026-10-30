"""Fixed synthetic contract tests; no exposure or catalogue files are read."""
import copy
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from scripts import reference_star_inputs as ref


def make_report():
    refs = [{'catalog': {'source_id': f's{i:02d}'},
             'split': 'training' if i < 14 else 'heldout'} for i in range(21)]
    train = [r['catalog']['source_id'] for r in refs[:14]]
    held = [r['catalog']['source_id'] for r in refs[14:]]
    configs = [{'spectral_configuration': name, 'training_source_ids': train[:],
                'heldout_source_ids': held[:]} for name in ('strict', 'broad')]
    return {'references': refs[::-1], 'configurations': configs}


def make_context():
    refs, training = ref.cohort(make_report())
    return ref.ReferenceContext([], {}, {}, refs, training, [], {})


def make_catalog_source():
    source = {'source_id': 's00', 'ra': 133.76, 'dec': -7.24,
              'ref_epoch': 2016., 'parallax': 12., 'pmra': 8., 'pmdec': -5.}
    for name in ref.gaia.PARAMETERS:
        source[name + '_error'] = 1. + ref.gaia.PARAMETERS.index(name) * .2
    for i, j in ref.gaia.PAIRS:
        source[f'{ref.gaia.PARAMETERS[i]}_{ref.gaia.PARAMETERS[j]}_corr'] = .2 if (i, j) == (0, 2) else 0.
    return source


class ReferenceInputsTests(unittest.TestCase):
    def test_all_21_and_allocation_preserved_independent_of_input_order(self):
        refs, training = ref.cohort(make_report())
        self.assertEqual([r['catalog']['source_id'] for r in refs], [f's{i:02d}' for i in range(21)])
        self.assertEqual(training, tuple(f's{i:02d}' for i in range(14)))
        self.assertEqual(sum(r['split'] == 'heldout' for r in refs), 7)

    def test_context_verifies_catalog_hash_and_snapshot_before_geometry(self):
        report = make_report()
        rows = [dict(r['catalog']) for r in report['references']]
        frames = [{'mjd': 58000. + i, 'image_header': {'test_mjd': 60000. + i},
                   'record': {'obs_id': f'f{i:02d}'}} for i in range(20)][::-1]
        manifest = {'gaia': {'path': 'synthetic.xml', 'sha256': 'good'}}
        time = lambda header: SimpleNamespace(
            midpoint=SimpleNamespace(utc=SimpleNamespace(mjd=header['test_mjd'])),
            metadata=lambda: {'synthetic': True})
        with patch.object(ref.original, 'read_verified_frames', return_value=(frames, manifest)), \
             patch.object(ref.RESULTS.__class__, 'read_text', side_effect=[json.dumps(report), json.dumps({'catalog': []})]), \
             patch.object(ref.original.lab, 'digest', return_value='good') as digest, \
             patch.object(ref.gaia, 'catalog_rows', return_value=rows), \
             patch.object(ref.timing, 'parse_image_header', side_effect=time), \
             patch.object(ref.quality, 'positions', return_value={}) as positions:
            context = ref.read_context()
            self.assertEqual(len(context.references), 21)
            self.assertEqual([f['record']['obs_id'] for f in context.frames], [f'f{i:02d}' for i in range(20)])
            self.assertEqual(context.frames[0]['mjd'], 60000.)
            self.assertEqual(context.frames[0]['legacy_mjd'], 58000.)
            digest.assert_called_once(); positions.assert_called_once()
        with patch.object(ref.original, 'read_verified_frames', return_value=(frames, manifest)), \
             patch.object(ref.RESULTS.__class__, 'read_text', return_value=json.dumps(report)), \
             patch.object(ref.original.lab, 'digest', return_value='wrong'), \
             patch.object(ref.quality, 'positions') as positions:
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                ref.read_context()
            positions.assert_not_called()
        rows[0]['unexpected'] = 1
        changed = copy.deepcopy(report); changed['references'][0]['catalog']['unexpected'] = 2
        with patch.object(ref.original, 'read_verified_frames', return_value=(frames, manifest)), \
             patch.object(ref.RESULTS.__class__, 'read_text', return_value=json.dumps(changed)), \
             patch.object(ref.original.lab, 'digest', return_value='good'), \
             patch.object(ref.gaia, 'catalog_rows', return_value=rows), \
             patch.object(ref.quality, 'positions') as positions:
            with self.assertRaisesRegex(ValueError, 'snapshot differs'):
                ref.read_context()
            positions.assert_not_called()

    def test_cohort_rejects_incomplete_duplicate_and_inconsistent_allocations(self):
        base = make_report()
        altered = []
        report = copy.deepcopy(base); report['references'].pop(); altered.append(report)
        report = copy.deepcopy(base); report['references'][0] = copy.deepcopy(report['references'][1]); altered.append(report)
        report = copy.deepcopy(base); report['configurations'][0]['heldout_source_ids'][0] = 's00'; altered.append(report)
        report = copy.deepcopy(base); report['configurations'][0]['training_source_ids'].reverse(); altered.append(report)
        report = copy.deepcopy(base); report['configurations'].pop(); altered.append(report)
        report = copy.deepcopy(base); report['configurations'].append(copy.deepcopy(report['configurations'][0])); altered.append(report)
        report = copy.deepcopy(base); report['references'][0]['split'] = 'training'; altered.append(report)
        for report in altered:
            with self.subTest(report=report), self.assertRaises(ValueError):
                ref.cohort(report)

    def test_registration_omits_evaluated_training_star_and_keeps_14_for_heldout(self):
        context = make_context(); frame = {'record': {'obs_id': 'frame'}}
        observed = []
        def registration(_frame, training, model):
            self.assertEqual(model, 'translation')
            ids = [r['catalog']['source_id'] for r in training]
            observed.append(ids)
            return {'source_ids': ids}
        with patch.object(ref.gaia, 'fit_registration', side_effect=registration):
            for item in context.references:
                result = ref.source_registration(context, item, frame)
                sid = item['catalog']['source_id']
                self.assertNotIn(sid, result['source_ids'])
                self.assertEqual(len(result['source_ids']), 13 if sid in context.training_ids else 14)
                self.assertEqual(set(result['source_ids']), set(context.training_ids) - {sid})
        self.assertEqual(len(observed), 21)

    def test_registration_rejects_leaked_evaluated_id(self):
        context = make_context()
        with patch.object(ref.gaia, 'fit_registration', return_value={'source_ids': ['s00']}):
            with self.assertRaisesRegex(ValueError, 'leaked'):
                ref.source_registration(context, context.references[0], {})

    def test_unique_id_and_separation_only_exclude_one_counterpart(self):
        cat = [{'id': 'self', 'gaia': {'source_id': 's00'}},
               {'id': 'z', 'gaia': {'source_id': 's01'}},
               {'id': 'a', 'gaia': None}, {'id': 'far', 'gaia': None}]
        positions = np.array([[.35, 0], [2, 0], [-1, 0], [9, 0]])
        target, neighbors = ref.counterpart_and_neighbors(cat, positions, 's00', np.zeros(2))
        self.assertEqual(target, 'self')
        self.assertEqual([name for name, _ in neighbors], ['a', 'z'])
        np.testing.assert_array_equal(neighbors[0][1], [-1, 0])

    def test_missing_ambiguous_or_duplicate_counterpart_fails(self):
        base = [{'id': 'self', 'gaia': {'source_id': 's00'}}, {'id': 'n', 'gaia': None}]
        cases = [
            (base, [[.351, 0], [1, 0]]),
            (base, [[.1, 0], [.2, 0]]),
            ([{'id': 'self', 'gaia': None}, base[1]], [[.1, 0], [1, 0]]),
            ([base[0], {'id': 'duplicate', 'gaia': {'source_id': 's00'}}], [[.1, 0], [1, 0]]),
        ]
        for catalog, xy in cases:
            with self.subTest(catalog=catalog, xy=xy), self.assertRaisesRegex(ValueError, 'counterpart'):
                ref.counterpart_and_neighbors(catalog, xy, 's00', np.zeros(2))

    def test_neighbor_limit_rejects_instead_of_truncating(self):
        cat = [{'id': 'self', 'gaia': {'source_id': 's00'}}] + [
            {'id': f'n{i:02d}', 'gaia': None, 'brightness': 100 - i} for i in range(25)]
        xy = np.array([[0., 0.]] + [[1. + i / 100., 0.] for i in range(25)])
        target, neighbors = ref.counterpart_and_neighbors(cat[:-1], xy[:-1], 's00', [0, 0])
        self.assertEqual(target, 'self'); self.assertEqual(len(neighbors), 24)
        with self.assertRaisesRegex(ValueError, 'no brightness-based truncation'):
            ref.counterpart_and_neighbors(cat, xy, 's00', [0, 0])

    def test_gaia_shared_five_parameter_covariance_cross_time_psd(self):
        source = make_catalog_source()
        frames = [{'mjd': mjd, 'record': {'obs_id': f'f{i}'}} for i, mjd in enumerate((59000., 59200., 59600.))]
        context = ref.ReferenceContext(frames, {}, {}, [], (), [], {})
        earth = lambda mjd: np.array([.2, .8, -.1]) if mjd == 59000. else np.array([-.6, .4, .3])
        with patch.object(ref.gaia, 'earth_position', side_effect=earth):
            result = ref.source_catalog_cross_time(context, {'catalog': source})
            plain = dict(source, parallax=0., pmra=0., pmdec=0.)
            moving = ref.prediction(source, frames[-1])[0]
            stationary = ref.prediction(plain, frames[-1])[0]
        self.assertGreater(np.linalg.norm(moving - stationary), 1e-4)
        cov = np.array(result['covariance_px2'])
        self.assertEqual(cov.shape, (6, 6))
        np.testing.assert_allclose(cov, cov.T, rtol=1e-12, atol=1e-18)
        self.assertGreater(np.linalg.norm(cov[:2, 2:4]), 0.)
        self.assertGreaterEqual(np.linalg.eigvalsh(cov).min(), -1e-12 * np.linalg.norm(cov, 2))
        self.assertEqual([t['obs_id'] for t in result['times']], ['f0', 'f1', 'f2'])

    def test_gaia_nonpositive_or_non_psd_covariance_refused(self):
        source = make_catalog_source()
        for bad in (dict(source, ra_error=-1), dict(source, ra_error=0),
                    dict(source, ra_dec_corr=2.)):
            with self.subTest(bad=bad), patch.object(ref.gaia, 'earth_position', return_value=np.zeros(3)):
                with self.assertRaises((ValueError, np.linalg.LinAlgError)):
                    ref.prediction(bad, {'mjd': 59000.})

    def test_nonfinite_gaia_prediction_fails(self):
        source = make_catalog_source()
        with patch.object(ref.gaia, 'gaia_xy', return_value=np.array([np.nan, 1.])), \
             patch.object(ref.gaia, 'gaia_jacobian', return_value=np.ones((2, 5))):
            with self.assertRaises(ValueError):
                ref.prediction(source, {'mjd': 59000.})

    def test_cell_guards_and_shared_preparation_for_both_psf_arms(self):
        context = make_context(); reference = context.references[0]
        context.catalog = [{'id': 'self', 'gaia': {'source_id': 's00'}}, {'id': 'n', 'gaia': None}]
        context.catalog_positions = {'f0': np.array([[0., 0.], [1., 0.]])}
        frame = {'data': np.zeros((40, 40)), 'record': {'obs_id': 'f0', 'epoch': 'before',
                 'path': 'synthetic', 'sha256': 'hash', 'cutout_url': 'synthetic'},
                 'exposure_time': {}, 'mjd': 59000.}
        yy, xx = np.mgrid[14:27, 14:27]
        sample = {'x': xx.ravel(), 'y': yy.ravel(), 'data': np.zeros(xx.size), 'error': np.ones(xx.size)}
        registration = {'offset': [0., 0.], 'offset_covariance': np.eye(2), 'source_ids': list(context.training_ids[1:])}
        with patch.object(ref, 'prediction', return_value=(np.zeros(2), np.ones((2, 5)), np.eye(5))), \
             patch.object(ref, 'source_registration', return_value=registration), \
             patch.object(ref.original, 'native_position', return_value=np.array([20., 20.])), \
             patch.object(ref.gaia.motion, 'native_stamp', return_value=sample):
            prepared, metadata = ref.prepare_cell(context, reference, frame)
            self.assertEqual(metadata['counterpart_excluded'], 'self')
            self.assertEqual(metadata['neighbor_ids'], ['n'])
            self.assertEqual(metadata['core_valid_fraction'], 1.)
            self.assertEqual(prepared['selection_mask'].sum(), len(sample['x']))
            with patch.object(ref.semantic, 'prepare_semantic', side_effect=lambda items, anchor, **kw: [{'item': items[0], **kw}]):
                a = ref.prepare_variant(prepared, np.zeros(2), 'nearest')
                b = ref.prepare_variant(prepared, np.zeros(2), 'bilinear')
            self.assertIs(a['item'], b['item'])
            self.assertEqual((a['background_order'], b['background_order']), (1, 1))
            self.assertEqual((a['epsf_kind'], b['epsf_kind']), ('nearest', 'bilinear'))
            with patch.object(ref.original, 'native_position', return_value=np.array([5., 5.])):
                with self.assertRaisesRegex(ValueError, 'edge margin'):
                    ref.prepare_cell(context, reference, frame)
            bad_sample = dict(sample, x=sample['x'][:20], y=sample['y'][:20])
            with patch.object(ref.gaia.motion, 'native_stamp', return_value=bad_sample):
                with self.assertRaisesRegex(ValueError, 'too few'):
                    ref.prepare_cell(context, reference, frame)
            off_core = (sample['x'] - 20.) ** 2 + (sample['y'] - 20.) ** 2 > 2.5 ** 2
            bad_core = dict(sample, x=sample['x'][off_core], y=sample['y'][off_core])
            with patch.object(ref.gaia.motion, 'native_stamp', return_value=bad_core):
                with self.assertRaisesRegex(ValueError, 'core mask coverage'):
                    ref.prepare_cell(context, reference, frame)


if __name__ == '__main__':
    unittest.main()
