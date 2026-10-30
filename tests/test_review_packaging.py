"""Verify the review contract and serverless packaging without scientific data."""
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReviewPackagingTest(unittest.TestCase):
    def test_contract_matches_canonical_projection_and_source_bytes(self):
        source_bytes = (ROOT / 'web/data/manifest.json').read_bytes()
        source = json.loads(source_bytes)
        contract = json.loads((ROOT / 'web/api/_review_manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(contract['source_manifest_sha256'], sha256(source_bytes).hexdigest())
        self.assertEqual(contract['analysis_sha256'], source['analysis_sha256'])
        expected = [{'id': s['id'], 'candidates': [{'id': c['id']} for c in s['candidates']],
                     'before': {'sha256': s['before']['sha256']}, 'after': {'sha256': s['after']['sha256']},
                     'target_detection': s['target_detection']} for s in source['scenes']]
        self.assertEqual(contract['scenes'], expected)
        subprocess.run([sys.executable, str(ROOT / 'scripts/build_review_contract.py'), '--check'], check=True,
                       capture_output=True, text=True)

    def test_review_validation_with_only_api_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shutil.copytree(ROOT / 'web/api', root / 'api', ignore=shutil.ignore_patterns('__pycache__'))
            program = '''
import sys
sys.path.insert(0, sys.argv[1])
from api import reviews
m = reviews.manifest()
for scene in m['scenes']:
    for selection in ['target'] + [c['id'] for c in scene['candidates']]:
        body = {'scene_id': scene['id'], 'selection': selection, 'status': 'uncertain', 'analysis_sha256': m['analysis_sha256']}
        result = reviews.validate_review(body)
        assert result['input_sha256'] == [scene['before']['sha256'], scene['after']['sha256']]
        assert result['target_detection'] == scene['target_detection']
        for change, error in [({'selection': 'unknown'}, 'unknown_selection'), ({'analysis_sha256': 'stale'}, 'stale_analysis')]:
            try:
                reviews.validate_review({**body, **change})
            except ValueError as exc:
                assert str(exc) == error
            else:
                raise AssertionError('invalid review accepted')
'''
            self.assertFalse((root / 'data').exists())
            subprocess.run([sys.executable, '-I', '-c', program, str(root)], cwd=root, check=True,
                           capture_output=True, text=True)

    def test_generator_write_and_check_fail_on_stale_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ('scripts/build_review_contract.py', 'web/data/manifest.json', 'web/api/_review_manifest.json'):
                dest = root / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, dest)
            script = root / 'scripts/build_review_contract.py'
            source = root / 'web/data/manifest.json'
            source.write_bytes(source.read_bytes() + b' ')
            check = subprocess.run([sys.executable, str(script), '--check'], capture_output=True, text=True)
            self.assertEqual(check.returncode, 1)
            self.assertIn('missing or stale', check.stderr)
            subprocess.run([sys.executable, str(script), '--write'], check=True, capture_output=True, text=True)
            subprocess.run([sys.executable, str(script), '--check'], check=True, capture_output=True, text=True)

    def test_functions_exclude_static_data_and_include_review_contract(self):
        config = json.loads((ROOT / 'web/vercel.json').read_text(encoding='utf-8'))['functions']
        self.assertEqual(config['api/reviews.py']['includeFiles'], 'api/_review_manifest.json')
        for name in ('api/reviews.py', 'api/observations.py', 'api/frame.py'):
            self.assertEqual(config[name]['excludeFiles'], '{data/**,assets/**,*.html,*.css,*.js,*.svg}')


if __name__ == '__main__':
    unittest.main()
