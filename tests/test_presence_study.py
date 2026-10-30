"""Small synthetic end-to-end journal/seal tests; no science simulation."""
from contextlib import ExitStack, redirect_stdout
from hashlib import sha256
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run_presence_study as study
from scripts import science_jobs


ROOT = Path(__file__).resolve().parents[1]
COMMIT = 'a' * 40
THRESHOLD_COMMIT = 'b' * 40


class PresenceStudyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.output = base / 'output'
        self.threshold = base / 'threshold.json'
        self.design = base / 'design.json'
        self.design.write_text('{"synthetic":true}', encoding='utf8')
        self.calls = []
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(study, 'OUTPUT', self.output))
        self.stack.enter_context(patch.object(study, 'GEOMETRY', self.output / 'geometry.json'))
        self.stack.enter_context(patch.object(study, 'THRESHOLD', self.threshold))
        self.stack.enter_context(patch.object(study, 'DESIGN', self.design))
        self.stack.enter_context(patch.object(study, 'RULES', {**study.RULES, 'draws_per_case': 2}))
        self.verify = self.stack.enter_context(patch.object(study.frozen, 'verify', return_value={}))
        self.stack.enter_context(patch.object(study.frozen, 'runtime', return_value={'synthetic': True}))
        self.stack.enter_context(patch.object(study.frozen, 'identity', side_effect=lambda path, commit, runtime, section:
                                            {'commit': commit, 'runtime': runtime, 'section': section}))
        self.build = self.stack.enter_context(patch.object(study.inputs, 'build_geometry', return_value={'snapshot': {'fixed': [1, 2]}}))
        self.draw = self.stack.enter_context(patch.object(study.inputs, 'realize', side_effect=self.realize))
        self.stack.enter_context(patch.object(study.inputs, 'score_data', side_effect=lambda context, data: {'combined': data[0]}))
        self.stack.enter_context(redirect_stdout(io.StringIO()))

    def realize(self, context, stage, scenario, draw):
        self.calls.append((stage, scenario, draw))
        if stage == 'validation' and (scenario, draw) in {(0, 1), (2, 1)}:
            raise ValueError('synthetic failure')
        return [float(scenario * 10 + draw)], {'realization_sha256': f'hash-{stage}-{scenario}-{draw}'}

    def committed_bytes(self, *args, **kwargs):
        return self.threshold.read_bytes()

    def test_full_planned_denominators_and_scaled_cases(self):
        with patch.object(study, 'RULES', {**study.RULES, 'draws_per_case': 999}):
            cal = study.expected_keys('calibration'); val = study.expected_keys('validation')
        self.assertEqual((len(cal), len(val), len(cal) + len(val)), (1998, 5994, 7992))
        self.assertEqual(len(set(cal + val)), 7992)
        self.assertEqual(len(study.expected_keys('calibration')), 4)
        self.assertEqual(len(study.expected_keys('validation')), 12)
        with self.assertRaises(ValueError): study.expected_keys('other')

    def test_threshold_is_max_across_cases_and_failed_calibration_abstains(self):
        keys = study.expected_keys('calibration')
        rows = [{'key': list(k), 'payload': {'status': 'score_completed', 'score': {'combined': float(i)}}}
                for i, k in enumerate(keys)]
        threshold = study.threshold_from_records(rows)
        self.assertEqual(threshold['threshold'], 3.)
        self.assertEqual(list(threshold['case_maxima'].values()), [1., 3.])
        rows[1]['payload'] = {'status': 'score_failed', 'error': 'failed'}
        with self.assertRaisesRegex(RuntimeError, 'abstains'):
            study.threshold_from_records(rows)
        with self.assertRaisesRegex(RuntimeError, 'incomplete'):
            study.threshold_from_records(rows[:-1])

    def test_geometry_uses_atomic_encoding_and_rejects_changed_snapshot(self):
        context = {'snapshot': {'fixed': [1, 2], 'variant': 'nearest'}}
        first = study.save_geometry(context)
        self.assertEqual(study.GEOMETRY.read_bytes(), science_jobs.encode(context['snapshot']))
        self.assertEqual(study.save_geometry(context), first)
        with self.assertRaisesRegex(RuntimeError, 'snapshot changed'):
            study.save_geometry({'snapshot': {'fixed': [2, 1]}})

    def test_sealed_calibration_and_validation_resume_without_redraw(self):
        study.run(COMMIT, 'calibration')
        self.assertEqual(len(self.calls), 4)
        document = study.seal(COMMIT)
        self.assertEqual(document['threshold'], 11.)
        self.assertFalse(document['validation_generated'])
        self.assertEqual(document['case_maxima'], {'plane_null': 1., 'quadratic_null': 11.})
        with patch.object(study.subprocess, 'check_output', side_effect=self.committed_bytes):
            study.run(COMMIT, 'validation', THRESHOLD_COMMIT)
            self.assertEqual(len(self.calls), 16)
            geometry_sha = study.legacy.lab.digest(study.GEOMETRY)
            val = study.open_journal(COMMIT, {'synthetic': True}, 'validation', geometry_sha,
                                     document, THRESHOLD_COMMIT)
            self.assertEqual(val.counts()['statuses'], {'score_completed': 10, 'score_failed': 2})
            failed = val.read(('validation', 'plane_null', '1'))['payload']
            self.assertEqual(failed['status'], 'score_failed')
            self.assertNotIn('accepted', failed)
            positive_failure = val.read(('validation', 'plane_300uJy', '1'))['payload']
            self.assertEqual(positive_failure['status'], 'score_failed')
            self.assertNotIn('accepted', positive_failure)
            self.assertFalse(val.read(('validation', 'quadratic_null', '1'))['payload']['accepted'])
            self.assertTrue(val.read(('validation', 'plane_300uJy', '0'))['payload']['accepted'])
            saved = val.records(require_complete=True)
            study.run(COMMIT, 'validation', THRESHOLD_COMMIT)
            self.assertEqual(len(self.calls), 16)
            self.assertEqual(val.records(require_complete=True), saved)
        with self.assertRaisesRegex(RuntimeError, 'sealed'):
            study.run(COMMIT, 'calibration')

    def test_uncommitted_and_changed_threshold_refuse_before_geometry_or_draw(self):
        with self.assertRaisesRegex(RuntimeError, 'commit'):
            study.run(COMMIT, 'validation', None)
        self.build.assert_not_called();self.draw.assert_not_called()
        self.verify.side_effect = RuntimeError('source or input mismatch')
        with self.assertRaisesRegex(RuntimeError, 'source or input mismatch'):
            study.run(COMMIT, 'validation', THRESHOLD_COMMIT)
        self.build.assert_not_called();self.draw.assert_not_called()
        self.verify.side_effect = None
        study.run(COMMIT, 'calibration');study.seal(COMMIT)
        self.build.reset_mock();self.draw.reset_mock()
        with patch.object(study.subprocess, 'check_output', return_value=b'not the threshold') as git:
            with self.assertRaisesRegex(RuntimeError, 'differ from committed'):
                study.run(COMMIT, 'validation', THRESHOLD_COMMIT)
            self.assertIn(THRESHOLD_COMMIT + ':', git.call_args.args[0][2])
        self.build.assert_not_called();self.draw.assert_not_called()

    def test_changed_calibration_checksum_and_wrong_protocol_refuse_validation(self):
        study.run(COMMIT, 'calibration');document = study.seal(COMMIT)
        geometry_sha = study.legacy.lab.digest(study.GEOMETRY)
        journal = study.open_journal(COMMIT, {'synthetic': True}, 'calibration', geometry_sha)
        key = study.expected_keys('calibration')[0]
        record = journal.read(key)
        body = {k: v for k, v in record.items() if k != 'checksum'}
        body['payload']['score']['combined'] = .5
        science_jobs.atomic(journal._record_path(key), {**body, 'checksum': sha256(science_jobs.encode(body)).hexdigest()})
        self.build.reset_mock();self.draw.reset_mock()
        with patch.object(study.subprocess, 'check_output', side_effect=self.committed_bytes):
            with self.assertRaisesRegex(RuntimeError, 'calibration records changed'):
                study.run(COMMIT, 'validation', THRESHOLD_COMMIT)
            with self.assertRaisesRegex(RuntimeError, 'identity changed'):
                study.run('c' * 40, 'validation', THRESHOLD_COMMIT)
        self.build.assert_not_called();self.draw.assert_not_called()
        self.assertTrue(document['calibration_digest'])


if __name__ == '__main__':
    unittest.main()
