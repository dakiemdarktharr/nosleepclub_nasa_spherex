"""Study ordering, refusal and complete denominators, using synthetic inputs."""
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

from scripts import run_shape_calibration as study
from scripts.experiment_journal import Journal


def context():
    return SimpleNamespace(
        training_ids=tuple(f's{i:02d}' for i in range(14)),
        references=[{'catalog': {'source_id': f's{i:02d}'},
                     'split': 'training' if i < 14 else 'heldout'} for i in range(21)],
        frames=[{'record': {'obs_id': f'f{i:02d}',
                            'epoch': '2025-11' if i < 10 else '2026-04'}} for i in range(20)])


def cells(scaled=(.2, -.1, .1)):
    rows = []
    for sid in range(8):
        for exp, epoch in (('f0', '2025-11'), ('f1', '2026-04')):
            rows.append({'key': [f's{sid}', exp], 'source_id': f's{sid}', 'obs_id': exp,
                         'epoch': epoch, 'x': [0, 1, 2], 'y': [0, 0, 0], 'error': [1., 1., 1.],
                         'shape_information_scaled': np.eye(3)*100.,
                         'shape_score_scaled': np.asarray(scaled)*100.,
                         'shape_score_pixel_response': np.eye(3)*10.})
    return rows


class ShapeCalibrationTests(unittest.TestCase):
    def test_source_and_time_reservations_are_disjoint_and_all_168_retained(self):
        ctx = context();keys, learn, reserved = study.planned_cells(ctx)
        self.assertEqual(len(keys), 168)
        self.assertEqual(len(set(keys)), 168)
        self.assertEqual(learn, [f'f{i:02d}' for i in (*range(6), *range(10, 16))])
        self.assertEqual(reserved, [f'f{i:02d}' for i in (*range(6, 10), *range(16, 20))])
        self.assertFalse(set(learn) & set(reserved))
        self.assertEqual({k[0] for k in keys}, set(ctx.training_ids))
        ctx.frames[0]['record']['obs_id'] = ctx.frames[1]['record']['obs_id']
        with self.assertRaises(ValueError):study.planned_cells(ctx)

    def test_unavailable_and_numerical_refusal_never_prepare_or_refit(self):
        ctx = context()
        for payload, status in (({'status': 'preparation_failed', 'error': 'old edge'}, 'baseline_unavailable'),
                                ({'status': 'fit_completed', 'fit': {'numerical_support': False,
                                  'numerical_reasons': ['old mode']}}, 'baseline_numerical_refusal')):
            with self.subTest(status=status), patch.object(study.baseline.inputs, 'prepare_cell') as prepare:
                row = study.cell_attempt(ctx, ctx.references[0], ctx.frames[0], {'payload': payload, 'checksum': 'saved'})
                self.assertEqual(row['status'], status);prepare.assert_not_called()

    def test_linear_score_recovers_known_vector_with_overlap_aware_error(self):
        rows = cells();diagnostic, reasons, values = study.numerical_summary(rows)
        self.assertEqual(reasons, [])
        np.testing.assert_allclose(values, np.array([.2, -.1, .1])*study.DEFAULT_BOUNDS, atol=1e-15)
        # Two exposures; eight stamps per exposure share the same three pixels.
        # Total response=80 I per exposure and F=1600 I, not 16 independent stamps.
        np.testing.assert_allclose(diagnostic['conditional_scaled_covariance'], np.eye(3)*.005, atol=1e-15)
        self.assertEqual(diagnostic['unique_original_pixels'], 6)
        self.assertFalse(diagnostic['weight_uncertainty_propagated'])

    def test_whole_candidate_refused_without_clipping_or_dimension_change(self):
        diagnostic, reasons, values = study.numerical_summary(cells(scaled=(1.01, 0., 0.)))
        self.assertIn('physical_parameter_bounds', reasons)
        self.assertIsNone(values)
        self.assertAlmostEqual(diagnostic['unconstrained_scaled_values'][0], 1.01)
        rows = cells()
        for cell in rows:cell['epoch'] = '2025-11'
        _, reasons, values = study.numerical_summary(rows)
        self.assertIn('season_source_support', reasons);self.assertIsNone(values)
        rows = cells()
        for cell in rows:cell['shape_score_pixel_response'] *= 10.
        _, reasons, values = study.numerical_summary(rows)
        self.assertIn('conditional_precision', reasons);self.assertIsNone(values)

    def test_verification_and_baseline_identity_precede_all_score_work(self):
        ctx = context();keys, _, _ = study.planned_cells(ctx)
        design = {'metadata': {'expected_keys': [list(k) for k in keys], 'baseline_journal_digest': 'old'}}
        with patch.object(study.frozen, 'verify', side_effect=RuntimeError('bad commit')), \
             patch.object(study, 'open_baseline') as opened, \
             patch.object(study, 'cell_attempt') as attempt:
            with self.assertRaisesRegex(RuntimeError, 'bad commit'):study.run('bad')
            opened.assert_not_called();attempt.assert_not_called()
        for mismatch in ('baseline_digest', 'expected_keys', 'runtime'):
            current = copy.deepcopy(design)
            if mismatch == 'expected_keys': current['metadata']['expected_keys'][0][0] = 'wrong'
            digest = 'wrong' if mismatch == 'baseline_digest' else 'old'
            with self.subTest(mismatch=mismatch), \
                 patch.object(study.frozen, 'verify', return_value=current), \
                 patch.object(study, 'open_baseline', return_value=(ctx, None, digest)), \
                 patch.object(study.frozen, 'runtime', side_effect=RuntimeError('runtime changed') if mismatch == 'runtime' else None), \
                 patch.object(study, 'cell_attempt') as attempt:
                with self.assertRaises((RuntimeError, ValueError)):study.run('synthetic')
                attempt.assert_not_called()

    def test_interrupted_resume_keeps_failures_and_never_attempts_reserved_cells(self):
        ctx = context();keys, learning, reserved = study.planned_cells(ctx)
        identity = {'protocol_commit': 'synthetic', 'section': 'test'}
        design = {'metadata': {'expected_keys': [list(k) for k in keys], 'baseline_journal_digest': 'old'}}
        calls = []
        fake_old = SimpleNamespace(read=lambda key: {'key': key, 'payload': {}, 'checksum': 'old-row'})
        with tempfile.TemporaryDirectory(dir=study.ROOT) as temp, ExitStack() as stack:
            output = Path(temp)/'experiment'
            stack.enter_context(patch.object(study, 'OUTPUT', output))
            stack.enter_context(patch.object(study, 'RESULT', output/'calibration-result.json'))
            stack.enter_context(patch.object(study.frozen, 'verify', return_value=design))
            stack.enter_context(patch.object(study.frozen, 'runtime', return_value={}))
            stack.enter_context(patch.object(study.frozen, 'identity', return_value=identity))
            stack.enter_context(patch.object(study, 'open_baseline', return_value=(ctx, fake_old, 'old')))
            def attempt(context, reference, frame, saved):
                key = (reference['catalog']['source_id'], frame['record']['obs_id'])
                calls.append(key)
                if len(calls) == 2: raise RuntimeError('synthetic interruption')
                return {'source_id': key[0], 'obs_id': key[1], 'key': list(key),
                        'status': 'linearization_failed', 'error': 'synthetic refusal'}
            stack.enter_context(patch.object(study, 'cell_attempt', side_effect=attempt))
            stack.enter_context(patch.object(study, 'numerical_summary', return_value=({}, ['no_information'], None)))
            stack.enter_context(redirect_stdout(io.StringIO()))
            with self.assertRaisesRegex(RuntimeError, 'interruption'):study.run('synthetic')
            first = calls[0]
            result = study.run('synthetic')
            self.assertEqual(calls.count(first), 1)
            self.assertEqual(result['counts'], {'linearization_failed': 168})
            self.assertEqual(set(calls), set(keys))
            self.assertTrue(all(sid in ctx.training_ids and obs in learning for sid, obs in calls))
            self.assertFalse(any(obs in reserved for _, obs in calls))
            self.assertEqual(result['heldout_outcomes'], 0)

    def test_complete_failure_denominators_resume_and_result_checksum(self):
        ctx = context();keys, _, _ = study.planned_cells(ctx)
        identity = {'protocol_commit': 'synthetic', 'section': 'test'}
        design = {'metadata': {'expected_keys': [list(k) for k in keys], 'baseline_journal_digest': 'old'}}
        fake_old = SimpleNamespace(read=lambda key: {'key': key, 'payload': {}, 'checksum': 'old-row'})
        with tempfile.TemporaryDirectory(dir=study.ROOT) as temp, ExitStack() as stack:
            output = Path(temp)/'experiment';result_path = output/'calibration-result.json'
            stack.enter_context(patch.object(study, 'OUTPUT', output))
            stack.enter_context(patch.object(study, 'RESULT', result_path))
            stack.enter_context(patch.object(study.frozen, 'verify', return_value=design))
            stack.enter_context(patch.object(study.frozen, 'runtime', return_value={}))
            identity_mock = stack.enter_context(patch.object(study.frozen, 'identity', return_value=identity))
            stack.enter_context(patch.object(study, 'open_baseline', return_value=(ctx, fake_old, 'old')))
            def attempt(context, reference, frame, saved):
                sid = reference['catalog']['source_id'];obs = frame['record']['obs_id']
                return {'source_id': sid, 'obs_id': obs, 'key': [sid, obs],
                        'status': 'baseline_unavailable', 'error': 'synthetic missing pixels'}
            attempt_mock = stack.enter_context(patch.object(study, 'cell_attempt', side_effect=attempt))
            stack.enter_context(patch.object(study, 'numerical_summary', return_value=({}, ['no_information'], None)))
            shape_guard = stack.enter_context(patch.object(study, 'shape_guard'))
            stack.enter_context(redirect_stdout(io.StringIO()))
            first = study.run('synthetic')
            self.assertEqual(first['planned'], 168)
            self.assertEqual(first['counts'], {'baseline_unavailable': 168})
            self.assertEqual(first['status'], 'candidate_rejected')
            self.assertFalse(first['promotion']);shape_guard.assert_not_called()
            self.assertEqual(attempt_mock.call_count, 168)
            attempt_mock.side_effect = AssertionError('must not rerun terminal outcomes')
            self.assertEqual(study.run('synthetic'), first)
            journal = Journal(output/'cells', identity, keys, study.STATUSES)
            self.assertEqual(len(journal.records(require_complete=True)), 168)
            identity_mock.return_value = {**identity, 'runtime': 'changed'}
            with self.assertRaisesRegex(ValueError, 'journal header identity'):study.run('synthetic')
            identity_mock.return_value = identity
            record_path = journal._record_path(keys[0]);record_bytes = record_path.read_bytes()
            record = json.loads(record_bytes);record['payload']['error'] = 'altered'
            record_path.write_bytes(study.legacy.encoded(record))
            with self.assertRaisesRegex(ValueError, 'corrupt journal'):study.run('synthetic')
            record_path.write_bytes(record_bytes)
            corrupt = copy.deepcopy(first);corrupt['promotion'] = True
            result_path.write_bytes(study.legacy.encoded(corrupt))
            with self.assertRaisesRegex(ValueError, 'identity changed'):study.run('synthetic')


if __name__ == '__main__':
    unittest.main()
