"""Freeze isolation, full factorial, durable failures and native estimands."""
from collections import Counter
from contextlib import ExitStack, redirect_stdout
import io
import gzip
from hashlib import sha256
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from scripts import run_signal_control_study as study
from scripts.experiment_journal import Journal
from scripts.science_jobs import encode


class SignalStudyTests(unittest.TestCase):
    def test_factorial_is_640_with_192_384_64_and_both_arms(self):
        keys = study.expected_keys()
        self.assertEqual(len(keys), 640)
        self.assertEqual(dict(Counter(k[0] for k in keys)), {'noiseless': 192, 'noisy': 384, 'null': 64})
        self.assertEqual(Counter(k[1] for k in keys), {sid: 320 for sid in study.GEOMETRIES})
        self.assertTrue(all({(*k[:-1], a) for a in study.ARMS} <= set(keys) for k in keys))
        self.assertEqual({k[3] for k in keys if k[0] == 'noisy'}, {'0', '3'})
        self.assertEqual({k[2] for k in keys if k[0] == 'noisy'}, {'gaussian'})

    def test_source_verification_precedes_any_context_or_generation(self):
        with patch.object(study.parent.frozen, 'verify', side_effect=RuntimeError('changed source')), \
             patch.object(study, 'open_inputs') as opened, patch.object(study.inputs, 'realize') as realized:
            with self.assertRaisesRegex(RuntimeError, 'changed source'): study.run('f'*40, 0)
        opened.assert_not_called(); realized.assert_not_called()

    def test_existing_assessment_refused_before_parent_design_read(self):
        with tempfile.TemporaryDirectory(dir=study.ROOT) as temp, \
             patch.object(study.parent.points, 'OUTPUT', Path(temp)), patch.object(study.parent.frozen, 'verify') as verified:
            (Path(temp)/'assessment').mkdir()
            with self.assertRaisesRegex(ValueError, 'unopened'): study.open_inputs()
        verified.assert_not_called()

    def test_changed_training_domain_refused(self):
        ctx = SimpleNamespace(training_ids=[study.GEOMETRIES[0]], frames=[{'record': {'obs_id': study.OBS_ID}}])
        with patch.object(study.parent.frozen, 'verify'), patch.object(study.parent, 'open_inputs', return_value=(ctx, None, None, np.zeros(3), {})):
            with self.assertRaisesRegex(ValueError, 'fixed old training'): study.open_inputs()

    def test_parent_archive_receipt_and_audit_source_are_bound(self):
        with tempfile.TemporaryDirectory(dir=study.ROOT) as temp, ExitStack() as stack:
            root = Path(temp); public = root/'public'; public.mkdir()
            source = root/'audit.py'; source.write_bytes(b'synthetic audit source')
            design = root/'design.json'; design.write_bytes(b'synthetic parent design')
            stack.enter_context(patch.object(study, 'ROOT', root))
            stack.enter_context(patch.object(study, 'PARENT_PUBLIC', public))
            stack.enter_context(patch.object(study, 'PARENT_AUDIT_SOURCES', ('audit.py',)))
            stack.enter_context(patch.object(study.parent, 'DESIGN', design))
            keys = [[str(i)] for i in range(112)]
            stack.enter_context(patch.object(study.parent, 'expected_keys', return_value=keys))
            def seal(value):
                return {**value, 'checksum': sha256(encode(value)).hexdigest()}
            def journal_digest(header, rows):
                value = {'header_sha256': sha256(encode(header)).hexdigest(),
                         'records': [{'key': r['key'], 'checksum': r['checksum']} for r in rows]}
                return sha256(study.parent.calibration.legacy.encoded(value)).hexdigest()
            profile_header = seal({'expected_keys': keys, 'identity_sha256': 'profile'})
            profile = [seal({'key': k, 'identity_sha256': 'profile', 'payload':
                            {'status': 'profile_completed' if i < 96 else 'preparation_failed'}})
                       for i, k in enumerate(keys)]
            identity = {'profile_commit': study.PARENT_COMMIT,
                        'profile_design_sha256': sha256(design.read_bytes()).hexdigest(),
                        'profile_journal_digest': journal_digest(profile_header, profile),
                        'source_sha256': {'audit.py': sha256(source.read_bytes()).hexdigest()},
                        'baseline_journal_digest': 'baseline', 'point_journal_digest': 'point'}
            audit_header = seal({'expected_keys': keys, 'identity_sha256': 'audit', 'identity': identity})
            audited = [seal({'key': k, 'identity_sha256': 'audit', 'payload': {
                'profile_checksum': p['checksum'], 'profile_status': p['payload']['status'],
                'status': 'verified' if i < 96 else 'verified_unavailable'}})
                for i, (k, p) in enumerate(zip(keys, profile))]
            receipt = {'schema': 'profile-landscape-independent-audit-1', 'status': 'passed',
                'planned': 112, 'counts': {'verified': 96, 'verified_unavailable': 16}, 'failures': [],
                'promotion': False, 'assessment_opened': False, 'identity': identity,
                'audit_cell_digest': journal_digest(audit_header, audited)}
            receipt['receipt_sha256'] = sha256(study.parent.calibration.legacy.encoded(receipt)).hexdigest()
            archive = {'schema': 'profile-landscape-records-1', 'design_sha256': identity['profile_design_sha256'],
                'journal_header': profile_header, 'records': profile, 'audit_journal_header': audit_header,
                'audit_records': audited, 'cell_digest': identity['profile_journal_digest']}
            raw = encode(archive); packed = gzip.compress(raw)
            overview = {'protocol_commit': study.PARENT_COMMIT, 'status': 'audited_diagnostic_only',
                'planned': 112, 'counts': {'profile_completed': 96, 'preparation_failed': 16},
                'cell_digest': identity['profile_journal_digest'], 'audit': {'receipt_sha256': receipt['receipt_sha256']},
                'promotion': False, 'assessment_opened': False,
                'download': {'bytes': len(packed), 'sha256': sha256(packed).hexdigest(),
                    'uncompressed_bytes': len(raw), 'uncompressed_sha256': sha256(raw).hexdigest()}}
            (public/'overview.json').write_text(json.dumps(overview), encoding='utf-8')
            (public/'independent-audit.json').write_text(json.dumps(receipt), encoding='utf-8')
            (public/'records.json.gz').write_bytes(packed)
            upstream = {'baseline_journal_digest': 'baseline', 'point_journal_digest': 'point'}
            self.assertEqual(study.verify_parent_products(None, upstream)['audit_receipt_sha256'], receipt['receipt_sha256'])
            source.write_bytes(b'tampered source')
            with self.assertRaisesRegex(ValueError, 'identity, source or outcome'): study.verify_parent_products(None, upstream)
            source.write_bytes(b'synthetic audit source')
            (public/'records.json.gz').write_bytes(packed+b'x')
            with self.assertRaisesRegex(ValueError, 'archive checksum'): study.verify_parent_products(None, upstream)

    def test_all_preparation_failures_kept_and_resume_does_not_retry(self):
        metadata = {'synthetic': 'no real data'}; identity = {'test-only': 1}
        with tempfile.TemporaryDirectory(dir=study.ROOT) as temp, ExitStack() as stack:
            output = Path(temp)/'output'; stack.enter_context(patch.object(study, 'OUTPUT', output))
            design = Path(temp)/'design.json'; design.write_text('{"fixture":true}', encoding='utf-8')
            stack.enter_context(patch.object(study, 'DESIGN', design))
            stack.enter_context(patch.object(study.parent.frozen, 'verify', return_value={'metadata': metadata}))
            stack.enter_context(patch.object(study, 'open_inputs', return_value=(None, np.zeros(3), metadata)))
            stack.enter_context(patch.object(study.parent.frozen, 'runtime', return_value={}))
            stack.enter_context(patch.object(study.parent.frozen, 'identity', return_value=identity))
            prepare = stack.enter_context(patch.object(study.inputs, 'prepare_geometry', side_effect=ValueError('synthetic unavailable')))
            realized = stack.enter_context(patch.object(study.inputs, 'realize'))
            fit = stack.enter_context(patch.object(study.parent.baseline.model, 'fit_epoch'))
            stack.enter_context(redirect_stdout(io.StringIO()))
            study.run('synthetic', 0); study.run('synthetic', 1); study.run('synthetic', 0)
            records = Journal(output/'cells', identity, study.expected_keys(), study.STATUSES).records(require_complete=True)
            self.assertEqual(len(records), 640); self.assertEqual(prepare.call_count, 8)
            self.assertEqual(Counter(r['payload']['status'] for r in records), {'preparation_failed': 640})
            realized.assert_not_called(); fit.assert_not_called()
            summary = study.summarize('synthetic')
            self.assertFalse(summary['metrics']['noiseless_clean_gate']['passed'])
            self.assertEqual(summary['metrics']['noiseless_clean_gate']['passed_count'], 0)
            self.assertIsNone(summary['metrics']['strata'][0]['all_completed']['mean_dx_dy_native_px'])
            self.assertTrue(summary['metrics']['old_assessment_blocked'])

    def test_attempt_measures_native_error_and_keeps_unsupported_completed_fit(self):
        g = {'anchor_common': np.array([1., 2.]), 'target_native': np.array([32.25, 44.75]),
             'companion_native': np.array([33.75, 44.75]), 'frame': {}, 'original_metadata': {'test': True}}
        row_fit = {'position': [1.1, 2.2], 'frames': [{'obs_id': study.OBS_ID, 'target_flux_jy': .0012}],
                   'numerical_support': False, 'numerical_reasons': ['synthetic refusal']}
        key = ('noisy', study.GEOMETRIES[0], 'gaussian', '0', 'modeled', '1200', '0', 'baseline')
        with patch.object(study.inputs, 'fit_item', return_value={}), \
             patch.object(study.parent.baseline.previous, 'descriptors', return_value=[]), \
             patch.object(study.parent.baseline.semantic, 'model_samples', return_value=[]), \
             patch.object(study.parent.baseline.model, 'fit_epoch', return_value=row_fit), \
             patch.object(study.inputs.original, 'native_position', return_value=np.array([32.27, 44.72])):
            result = study.attempt(g, {'metadata': {'synthetic': True}}, key)
        self.assertEqual(result['status'], 'fit_completed'); self.assertIs(result['numerical_support'], False)
        np.testing.assert_allclose(result['position_native_error'], [.02, -.03])
        self.assertAlmostEqual(result['distance_to_companion_native'], np.hypot(1.48, .03))

    def test_null_uses_phase_anchor_without_inventing_position_truth(self):
        g = {'anchor_common': np.array([1., 2.]), 'target_common': np.array([1.4, 2.3]),
             'target_native': np.array([32.75, 44.75]), 'companion_native': np.array([34.25, 44.75]),
             'frame': {}, 'original_metadata': {'test': True}}
        fit = {'position': [1.5, 2.4], 'frames': [{'obs_id': study.OBS_ID, 'target_flux_jy': -.0001}],
               'numerical_support': True}
        key = ('null', study.GEOMETRIES[0], 'none', '3', 'isolated', '0', '0', 'corrected')
        with patch.object(study.inputs, 'fit_item', return_value={}), \
             patch.object(study.parent.baseline.previous, 'descriptors', return_value=[]), \
             patch.object(study.parent.baseline.semantic, 'model_samples', return_value=[]), \
             patch.object(study.parent.baseline.model, 'fit_epoch', return_value=fit) as fitter, \
             patch.object(study.inputs.original, 'native_position', return_value=np.array([32.8, 44.8])):
            result = study.attempt(g, {'metadata': {'synthetic': True}}, key)
        np.testing.assert_array_equal(fitter.call_args.args[1], g['target_common'])
        self.assertEqual(result['search_anchor_common'], [1.4, 2.3])
        self.assertIsNone(result['position_native_error'])
        self.assertIsNone(result['distance_to_companion_native'])
        self.assertEqual(result['true_flux_jy'], 0.)


if __name__ == '__main__': unittest.main()
