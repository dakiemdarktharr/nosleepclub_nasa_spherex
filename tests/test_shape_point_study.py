"""Staged point-study isolation, complete denominators and immutable resume."""
from contextlib import ExitStack, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from scripts import run_shape_point_study as study
from scripts.experiment_journal import Journal
from tests.test_shape_calibration import context


class ShapePointStudyTests(unittest.TestCase):
    def test_failed_calibration_summary_defers_252_and_never_opens_assessment(self):
        ctx = context();allocation = study.allocations(ctx)
        records = [{'key': list(k), 'payload': {'status': 'preparation_failed', 'error': 'synthetic'}}
                   for k in allocation['calibration']]
        journal = SimpleNamespace(records=lambda **_: records)
        old = SimpleNamespace(read=lambda key: {'payload': {'status': 'preparation_failed', 'error': 'old'}})
        gate = {'point_protocol_commit': 'synthetic', 'shape_calibration_cell_digest': 'score',
                'coefficient_seal_sha256': 'seal-sha', 'calibration_point_digest': 'point', 'assessment_allowed': False}
        with tempfile.TemporaryDirectory(dir=study.ROOT) as temp, ExitStack() as stack:
            output = Path(temp)/'output';output.mkdir();gate_path = Path(temp)/'gate.json'
            gate_path.write_text(json.dumps(gate), encoding='utf-8')
            stack.enter_context(patch.object(study, 'OUTPUT', output))
            stack.enter_context(patch.object(study, 'GATE', gate_path))
            stack.enter_context(patch.object(study.frozen, 'verify', return_value={'metadata': {
                'expected_keys': study.legacy.jsonable(allocation), 'baseline_journal_digest': 'old'}}))
            stack.enter_context(patch.object(study.calibration, 'open_baseline', return_value=(ctx, old, 'old')))
            stack.enter_context(patch.object(study, 'read_coefficients', return_value=({'cell_digest': 'score'}, np.zeros(3))))
            opened = stack.enter_context(patch.object(study, 'open_journal', return_value=journal))
            stack.enter_context(patch.object(study.calibration, 'record_digest', return_value='point'))
            stack.enter_context(patch.object(study.legacy.lab, 'digest', return_value='seal-sha'))
            stack.enter_context(redirect_stdout(io.StringIO()))
            result = study.summarize('synthetic')
            self.assertEqual((result['planned'], result['recorded'], result['deferred']), (420, 168, 252))
            self.assertEqual(result['primary']['point_status_counts']['missing'], 56)
            self.assertFalse(result['primary']['developmental_gates_passed'])
            self.assertEqual(len(result['source_rows']), 21)
            self.assertEqual(opened.call_count, 1)
            self.assertEqual(opened.call_args.args[1], 'calibration')
            self.assertFalse(result['promotion'])

    def test_gate_checks_every_saved_information_cell_and_both_error_budgets(self):
        ctx = context();alloc = study.legacy.jsonable(study.allocations(ctx))
        keys = study.allocations(ctx)['calibration'][:20]
        score_records = [{'key': list(key), 'payload': {'status': 'information_available',
                          'position_shape_response': [[0., 0., 0.], [0., 0., 0.]]}} for key in keys]
        metadata = {'expected_keys': alloc, 'baseline_journal_digest': 'old',
                    'shape_calibration_cell_digest': 'sealed-score', 'coefficient_seal_sha256': 'seal-sha'}
        for mode in ('pass', 'unsupported', 'p90', 'maximum'):
            rows = {}
            for i, key in enumerate(keys):
                error = .021 if mode == 'p90' else (.051 if mode == 'maximum' and i == 0 else .0)
                rows[key] = {'payload': {'status': 'fit_completed',
                    'fit': {'numerical_support': not (mode == 'unsupported' and i == 0),
                            'numerical_reasons': ['synthetic refusal']},
                    'position_change_common_px': [error, 0.]}}
            points = SimpleNamespace(records=lambda **_: list(rows.values()), read=lambda key: rows[key])
            score = SimpleNamespace(records=lambda **_: score_records)
            def digest(journal, records): return 'sealed-score' if journal is score else 'point'
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(dir=study.ROOT) as temp, \
                 patch.object(study, 'GATE', Path(temp)/'gate.json'), \
                 patch.object(study.frozen, 'verify', return_value={'metadata': metadata}), \
                 patch.object(study.calibration, 'open_baseline', return_value=(ctx, None, 'old')), \
                 patch.object(study, 'read_coefficients', return_value=({'cell_digest': 'sealed-score',
                    'shape_checks': {'passed': len(keys), 'planned': len(keys)}}, np.zeros(3))), \
                 patch.object(study, 'open_journal', return_value=points), \
                 patch.object(study.frozen, 'runtime', return_value={}), \
                 patch.object(study.frozen, 'identity', return_value={'section': 'synthetic'}), \
                 patch.object(study, 'Journal', return_value=score), \
                 patch.object(study.calibration, 'record_digest', side_effect=digest), \
                 patch.object(study.legacy.lab, 'digest', return_value='seal-sha'), \
                 redirect_stdout(io.StringIO()):
                gate = study.calibration_gate('synthetic')
                self.assertEqual(gate['assessment_allowed'], mode == 'pass')
                if mode == 'unsupported':self.assertIn('old_numerical_cell_no_longer_supported', gate['reasons'])
                if mode == 'p90':self.assertIn('linearization_p90', gate['reasons'])
                if mode == 'maximum':self.assertIn('linearization_maximum', gate['reasons'])

    def test_gate_refuses_score_journal_digest_changed_from_seal(self):
        ctx = context();alloc = study.legacy.jsonable(study.allocations(ctx))
        metadata = {'expected_keys': alloc, 'baseline_journal_digest': 'old',
                    'shape_calibration_cell_digest': 'sealed-score', 'coefficient_seal_sha256': 'seal-sha'}
        point = SimpleNamespace(records=lambda **_: [])
        score = SimpleNamespace(records=lambda **_: [])
        def digest(journal, records):
            return 'changed-score' if journal is score else 'point'
        with tempfile.TemporaryDirectory(dir=study.ROOT) as temp, \
             patch.object(study, 'GATE', Path(temp)/'gate.json'), \
             patch.object(study.frozen, 'verify', return_value={'metadata': metadata}), \
             patch.object(study.calibration, 'open_baseline', return_value=(ctx, None, 'old')), \
             patch.object(study, 'read_coefficients', return_value=({'cell_digest': 'sealed-score'}, np.zeros(3))), \
             patch.object(study, 'open_journal', return_value=point), \
             patch.object(study.frozen, 'runtime', return_value={}), \
             patch.object(study.frozen, 'identity', return_value={'section': 'synthetic'}), \
             patch.object(study, 'Journal', return_value=score), \
             patch.object(study.calibration, 'record_digest', side_effect=digest), \
             patch.object(study.legacy.lab, 'digest', return_value='seal-sha'), \
             redirect_stdout(io.StringIO()):
            with self.assertRaises(ValueError):study.calibration_gate('synthetic')
            self.assertFalse(study.GATE.exists())

    def test_gate_refuses_changed_baseline_before_opening_point_journal(self):
        ctx = context();alloc = study.legacy.jsonable(study.allocations(ctx))
        metadata = {'expected_keys': alloc, 'baseline_journal_digest': 'old',
                    'shape_calibration_cell_digest': 'sealed-score', 'coefficient_seal_sha256': 'seal-sha'}
        with patch.object(study.frozen, 'verify', return_value={'metadata': metadata}), \
             patch.object(study.calibration, 'open_baseline', return_value=(ctx, None, 'different')), \
             patch.object(study, 'read_coefficients', return_value=({'cell_digest': 'sealed-score'}, np.zeros(3))), \
             patch.object(study, 'open_journal') as points:
            with self.assertRaises(ValueError):study.calibration_gate('synthetic')
            points.assert_not_called()

    def test_allocation_calibration_assessment_and_primary(self):
        rows = study.allocations(context())
        self.assertEqual({k: len(v) for k, v in rows.items()}, {'calibration': 168, 'assessment': 252, 'primary': 56})
        self.assertFalse(set(rows['calibration']) & set(rows['assessment']))
        self.assertEqual(len(set(rows['calibration']+rows['assessment'])), 420)
        self.assertTrue(set(rows['primary']) <= set(rows['assessment']))
        self.assertFalse({k[0] for k in rows['primary']} & set(context().training_ids))

    def test_prior_unavailable_cell_keeps_failure_without_preparation(self):
        ctx = context();saved = {'checksum': 'old', 'payload': {'status': 'preparation_failed', 'error': 'old edge'}}
        with patch.object(study.baseline.inputs, 'prepare_cell') as prepare:
            result = study.attempt(ctx, ctx.references[0], ctx.frames[0], saved, np.zeros(3))
        prepare.assert_not_called()
        self.assertEqual(result['status'], 'preparation_failed')
        self.assertEqual(result['failure_stage'], 'reused_baseline_unavailable')
        self.assertEqual(result['baseline_checksum'], 'old')

    def test_assessment_refused_before_preparing_without_committed_passing_gate(self):
        ctx = context();allocations = study.legacy.jsonable(study.allocations(ctx))
        with patch.object(study.frozen, 'verify', return_value={'metadata': {
                'expected_keys': allocations, 'baseline_journal_digest': 'old'}}), \
             patch.object(study.calibration, 'open_baseline', return_value=(ctx, None, 'old')), \
             patch.object(study, 'read_coefficients', return_value=({}, np.zeros(3))), \
             patch.object(study, 'open_journal') as journal, patch.object(study, 'attempt') as attempt:
            with self.assertRaisesRegex(ValueError, 'committed calibration gate'):
                study.run('synthetic', 'assessment')
        journal.assert_not_called();attempt.assert_not_called()

    def test_calibration_all_168_keeps_failures_and_never_touches_reserved(self):
        ctx = context();allocations = study.allocations(ctx)
        identity = {'section': 'synthetic-calibration'}
        with tempfile.TemporaryDirectory(dir=study.ROOT) as temp, ExitStack() as stack:
            stack.enter_context(patch.object(study, 'OUTPUT', Path(temp)/'point'))
            stack.enter_context(patch.object(study.frozen, 'verify', return_value={'metadata': {
                'expected_keys': study.legacy.jsonable(allocations), 'baseline_journal_digest': 'old'}}))
            stack.enter_context(patch.object(study.frozen, 'runtime', return_value={}))
            stack.enter_context(patch.object(study.frozen, 'identity', return_value=identity))
            old = SimpleNamespace(read=lambda key: {'checksum': 'old'})
            stack.enter_context(patch.object(study.calibration, 'open_baseline', return_value=(ctx, old, 'old')))
            stack.enter_context(patch.object(study, 'read_coefficients', return_value=({}, np.zeros(3))))
            seen = []
            def attempt(context, reference, frame, saved, values):
                key = (reference['catalog']['source_id'], frame['record']['obs_id']);seen.append(key)
                self.assertIn(key, allocations['calibration'])
                return {'status': 'preparation_failed', 'error': 'synthetic missing', 'elapsed_seconds': 0.}
            mocked = stack.enter_context(patch.object(study, 'attempt', side_effect=attempt))
            stack.enter_context(redirect_stdout(io.StringIO()))
            study.run('synthetic', 'calibration')
            journal = Journal(study.OUTPUT/'calibration', identity, allocations['calibration'], study.STATUSES)
            first = journal.records(require_complete=True)
            self.assertEqual(len(first), 168);self.assertEqual(set(seen), set(allocations['calibration']))
            mocked.side_effect = AssertionError('no terminal outcome rerun')
            study.run('synthetic', 'calibration')
            self.assertEqual(journal.records(require_complete=True), first)
            self.assertFalse((study.OUTPUT/'assessment').exists())

    def test_gate_exact_git_bytes_and_supported_status_required(self):
        ctx = context()
        for commit in (None, 'abc', 'x'*40):
            with self.subTest(commit=commit), self.assertRaises(ValueError):
                study.verify_assessment_gate(commit, 'point', ctx)
        with tempfile.TemporaryDirectory(dir=study.ROOT) as temp:
            path = Path(temp)/'gate.json';path.write_text('{}', encoding='utf-8')
            with patch.object(study, 'GATE', path), \
                 patch.object(study.subprocess, 'check_output', return_value=b'{"different":true}'):
                with self.assertRaisesRegex(ValueError, 'Git bytes differ'):
                    study.verify_assessment_gate('a'*40, 'point', ctx)


if __name__ == '__main__':
    unittest.main()
