"""Synthetic runner checks, with no FITS load or new sky work."""
from contextlib import ExitStack, redirect_stdout
import copy
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from scripts import run_reference_covariance_study as study
from scripts.experiment_journal import Journal


def context():
    return SimpleNamespace(training_ids=tuple(f's{i:02d}' for i in range(14)),
        references=[{'catalog': {'source_id': f's{i:02d}'}} for i in range(21)],
        frames=[{'record': {'obs_id': f'e{i:02d}'}} for i in range(20)])


def synthetic_cells():
    rows = [];J = np.zeros((2, 5));J[0, 0] = J[1, 1] = 1.
    for sid in range(7):
        for exposure in ('e0', 'e1'):
            rows.append({'key': [f's{sid}', exposure], 'source_id': f's{sid}', 'obs_id': exposure,
                'x': [0, 1+2*sid, 2+2*sid], 'y': [0, 0, 0], 'error': [1., 1., 1.],
                'position_pixel_influence': [[.1, .3, 0.], [-.1, 0., .4]],
                'raw_offset_px': [.01*sid + (.1 if exposure == 'e0' else -.1), .02*sid],
                'metadata': {'gaia_jacobian_px_per_catalog_unit': J,
                             'gaia_covariance_catalog_units': np.eye(5)*.01}})
    return rows


class ReferenceCovarianceStudyTests(unittest.TestCase):
    def test_saved_point_reconstruction_adds_registration_and_has_zero_shape(self):
        ctx = context();ref = ctx.references[0];frame = ctx.frames[0]
        meta = {'anchor_sky_px': [4., 8.], 'registration_offset_px': [.3, -.2]}
        saved = {'checksum': 'old', 'payload': {'status': 'fit_completed', 'metadata': meta,
                 'fit': {'numerical_support': True, 'position': [4.2, 8.1]}}}
        item = {'data': [1., 2., 3.], 'error': [1., 1., 1.], 'neighbor_ids': ['n'],
                'metadata': {'x': [1, 2, 3], 'y': [4, 4, 4]}}
        def influence(actual, fit, anchor):
            np.testing.assert_array_equal(actual['shape_renderer'](fit['position']), np.zeros((3, 3)))
            np.testing.assert_array_equal(actual['neighbor_shape_design'], np.zeros((3, 1, 3)))
            self.assertEqual(anchor, meta['anchor_sky_px'])
            return {'position_pixel_influence': np.ones((2, 3)),
                    'position_derivative_step_common_px': .002, 'condition': 2.}
        with patch.object(study.baseline.inputs, 'prepare_cell', return_value=({}, meta)), \
             patch.object(study.baseline.inputs, 'prepare_variant', return_value=item) as prepare, \
             patch.object(study, 'centroid_and_shape_influence', side_effect=influence):
            row = study.cell_attempt(ctx, ref, frame, saved)
            self.assertEqual(row['status'], 'influence_available')
            np.testing.assert_allclose(row['raw_offset_px'], [.5, -.1])
            self.assertEqual(prepare.call_args.args[-1], 'nearest')
        for payload in ({'status': 'preparation_failed', 'error': 'old'},
                        {'status': 'fit_completed', 'fit': {'numerical_support': False, 'numerical_reasons': ['old']}}):
            with patch.object(study.baseline.inputs, 'prepare_cell') as prepare:
                row = study.cell_attempt(ctx, ref, frame, {'checksum': 'old', 'payload': payload})
                self.assertIn(row['status'], ('baseline_unavailable', 'baseline_numerical_refusal'))
                prepare.assert_not_called()
        with patch.object(study.baseline.inputs, 'prepare_cell', return_value=({}, {**meta, 'extra': True})):
            self.assertEqual(study.cell_attempt(ctx, ref, frame, saved)['status'], 'linearization_failed')

    def test_overlap_catalogue_covariance_and_heldout_frame(self):
        rows = synthetic_cells();train = [f's{i}' for i in range(5)];held = ['s5', 's6', 'missing']
        result = study.assemble(rows, train, ['e0', 'e1'], held)
        pixel = np.asarray(result['pixel_covariance_px2']);cat = np.asarray(result['catalogue_covariance_px2'])
        total = np.asarray(result['total_covariance_px2'])
        # s0 and s1 share the first native pixel of e0, including signed XY covariance.
        np.testing.assert_allclose(pixel[:2, 4:6], [[.01, -.01], [-.01, .01]], atol=1e-14)
        np.testing.assert_allclose(pixel[:2, 2:4], 0., atol=1e-14)
        np.testing.assert_allclose(cat[:2, 2:4], np.eye(2)*.01, atol=1e-14)
        np.testing.assert_allclose(cat[:2, 4:6], 0., atol=1e-14)
        np.testing.assert_allclose(total, pixel+cat, atol=1e-14)
        self.assertEqual(result['frame']['training_counts'], [5, 5])
        self.assertEqual(result['heldout_joint']['dof'], 8)
        self.assertEqual(result['heldout_by_source']['s5']['dof'], 4)
        self.assertEqual(result['heldout_by_source']['missing'], {'available': 0, 'chi2': None, 'dof': 0})
        self.assertEqual(result['row_order'], [c['key'] for c in rows])
        self.assertEqual(result['unique_original_pixels'], 30)
        for i, row in enumerate(result['rows']):
            frame = result['frame']['exposure_ids'].index(row['key'][1])
            np.testing.assert_allclose(row['frame_corrected_offset_px'],
                                       np.asarray(row['raw_offset_px'])-result['frame']['translation_px'][frame])
            self.assertEqual(row['heldout_marginal_mahalanobis2'] is not None, i >= 10)
        with self.assertRaisesRegex(ValueError, 'too few'):
            study.assemble(rows, train[:3], ['e0', 'e1'], ['s3', 's4', 's5', 's6'])
        bad = copy.deepcopy(rows);bad[1]['metadata']['gaia_covariance_catalog_units'][0, 0] = .02
        with self.assertRaisesRegex(ValueError, 'Gaia covariance changed'):
            study.assemble(bad, train, ['e0', 'e1'], held)

    def test_verification_denominator_resume_and_checksum(self):
        ctx = context();keys, exposures = study.planned_cells(ctx)
        self.assertEqual(len(keys), 420)
        design = {'metadata': {'expected_keys': [list(k) for k in keys], 'baseline_journal_digest': 'old',
                  'training_ids': list(ctx.training_ids), 'planned_exposures': exposures,
                  'heldout_ids': [f's{i:02d}' for i in range(14, 21)]}}
        with patch.object(study.frozen, 'verify', side_effect=RuntimeError('bad commit')), \
             patch.object(study.shape, 'open_baseline') as opened, patch.object(study, 'cell_attempt') as attempt:
            with self.assertRaisesRegex(RuntimeError, 'bad commit'):study.run('bad')
            opened.assert_not_called();attempt.assert_not_called()
        altered = copy.deepcopy(design);altered['metadata']['baseline_journal_digest'] = 'different'
        with patch.object(study.frozen, 'verify', return_value=altered), \
             patch.object(study.shape, 'open_baseline', return_value=(ctx, None, 'old')), \
             patch.object(study, 'cell_attempt') as attempt:
            with self.assertRaisesRegex(ValueError, 'baseline journal'):study.run('synthetic')
            attempt.assert_not_called()
        old = SimpleNamespace(read=lambda key: {'key': key, 'payload': {}, 'checksum': 'old-row'})
        identity = {'protocol_commit': 'synthetic', 'runtime': 'synthetic'};calls = []
        with tempfile.TemporaryDirectory(dir=study.ROOT) as temp, ExitStack() as stack:
            output = Path(temp)/'experiment';result_path = output/'covariance-result.json'
            stack.enter_context(patch.object(study, 'OUTPUT', output));stack.enter_context(patch.object(study, 'RESULT', result_path))
            stack.enter_context(patch.object(study.frozen, 'verify', return_value=design))
            stack.enter_context(patch.object(study.frozen, 'runtime', return_value={}))
            stack.enter_context(patch.object(study.frozen, 'identity', return_value=identity))
            stack.enter_context(patch.object(study.shape, 'open_baseline', return_value=(ctx, old, 'old')))
            def attempt(context, reference, frame, saved):
                sid = reference['catalog']['source_id'];obs = frame['record']['obs_id'];calls.append((sid, obs))
                if len(calls) == 2: raise RuntimeError('interruption')
                return {'source_id': sid, 'obs_id': obs, 'status': 'baseline_unavailable', 'error': 'synthetic'}
            stack.enter_context(patch.object(study, 'cell_attempt', side_effect=attempt))
            stack.enter_context(redirect_stdout(io.StringIO()))
            with self.assertRaisesRegex(RuntimeError, 'interruption'):study.run('synthetic')
            first = calls[0];result = study.run('synthetic')
            self.assertEqual(calls.count(first), 1)
            self.assertEqual(result['planned'], 420)
            self.assertEqual(result['counts'], {'baseline_unavailable': 420})
            self.assertEqual(sum(x['planned'] for x in result['source_counts'].values()), 420)
            self.assertEqual(result['status'], 'diagnostic_unavailable')
            self.assertFalse(result['promotion']);self.assertEqual(study.run('synthetic'), result)
            journal = Journal(output/'cells', identity, keys, study.STATUSES)
            self.assertEqual(len(journal.records(require_complete=True)), 420)
            valid_bytes = result_path.read_bytes()
            result_path.write_bytes(valid_bytes.replace(b'"diagnostic": null', b'"diagnostic": NaN'))
            with self.assertRaisesRegex(ValueError, 'nonfinite result'):study.run('synthetic')
            result_path.write_bytes(valid_bytes)
            corrupt = copy.deepcopy(result);corrupt['promotion'] = True
            result_path.write_bytes(study.legacy.encoded(corrupt))
            with self.assertRaisesRegex(ValueError, 'identity changed'):study.run('synthetic')


if __name__ == '__main__': unittest.main()
