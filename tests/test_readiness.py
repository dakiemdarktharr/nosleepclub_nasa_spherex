"""Readiness report never equates software checks or self-comparison with science."""
from contextlib import redirect_stdout
from io import StringIO
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('readiness', ROOT / 'scripts/check_readiness.py')
readiness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(readiness)


class ReadinessTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        files = ['web/vercel.json', 'web/requirements.txt', 'requirements.txt', 'web/api/reviews.py',
                 'web/api/observations.py', 'web/api/frame.py', 'web/data/manifest.json', 'web/data/gaia/results.json',
                 'web/data/ablation/validation-summary.json', 'web/data/ablation/validation-protocol.json',
                 'docs/PRODUCTION_READINESS.md', 'docs/REVIEW_API_CONTRACT.md',
                 'docs/OBSERVATION_API_CONTRACT.md', 'docs/FRAME_API_CONTRACT.md']
        result = json.loads((ROOT / 'web/data/gaia/results.json').read_text(encoding='utf-8'))
        files.extend('scripts/' + name for name in result['source_sha256'])
        for name in files:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)

    def test_actual_failure_and_self_comparison_are_exposed(self):
        result = readiness.collect(self.root)
        self.assertTrue(result['repository_checks_passed'])
        science = result['evidence']['science_0_9']
        self.assertTrue(science['comparison_is_self'])
        self.assertTrue(science['point_passed'])
        self.assertFalse(science['coverage_passed'])
        self.assertFalse(science['overall_passed'])
        self.assertFalse(result['scientific_ready'])
        self.assertEqual(result['software_test_status'], 'not_executed_by_this_report')
        self.assertEqual(len(result['evidence']['ledger']['items']), 20)

    def test_even_success_flags_and_closed_ledger_do_not_self_promote(self):
        summary_path = self.root / 'web/data/ablation/validation-summary.json'
        summary = json.loads(summary_path.read_text(encoding='utf-8'))
        summary['passed'] = summary['point_passed'] = summary['coverage_gate']['passed'] = True
        summary_path.write_text(json.dumps(summary), encoding='utf-8')
        ledger = self.root / 'docs/PRODUCTION_READINESS.md'
        ledger.write_text(ledger.read_text(encoding='utf-8').replace('Open |', 'Verified |').replace('In progress', 'Verified'), encoding='utf-8')
        result = readiness.collect(self.root)
        self.assertTrue(result['repository_checks_passed'])
        self.assertTrue(result['evidence']['science_0_9']['comparison_is_self'])
        self.assertFalse(result['scientific_ready'])

    def test_detects_bad_config_and_provenance(self):
        config_path = self.root / 'web/vercel.json'
        config = json.loads(config_path.read_text(encoding='utf-8'))
        config['functions']['api/frame.py']['maxDuration'] = 10
        config_path.write_text(json.dumps(config), encoding='utf-8')
        protocol = self.root / 'web/data/ablation/validation-protocol.json'
        protocol.write_text(protocol.read_text(encoding='utf-8') + ' ', encoding='utf-8')
        result = readiness.collect(self.root)
        checks = {c['name']: c['passed'] for c in result['repository_checks']}
        self.assertFalse(checks['serverless_config'])
        self.assertFalse(checks['validation_protocol'])
        self.assertFalse(result['repository_checks_passed'])
        self.assertFalse(result['scientific_ready'])

    def test_cli_requires_science_when_requested(self):
        report = readiness.collect(self.root)
        with patch.object(readiness, 'collect', return_value=report), redirect_stdout(StringIO()) as out:
            self.assertEqual(readiness.main([]), 0)
            self.assertEqual(readiness.main(['--require-science']), 1)
        self.assertIn('"scientific_ready": false', out.getvalue())


if __name__ == '__main__':
    unittest.main()
