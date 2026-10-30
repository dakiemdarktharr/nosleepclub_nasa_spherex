from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import frozen_experiment as frozen


class FrozenExperimentTests(unittest.TestCase):
    def test_design_refuses_overwrite_and_binds_commit_bytes(self):
        with tempfile.TemporaryDirectory(dir=frozen.ROOT / 'data/raw/benchmark') as temp:
            root = Path(temp);design = root / 'design.json';source = root / 'module.py'
            source.write_text('fixed source\n', encoding='utf-8')
            inventory = {'sources': {'module.py': sha256(source.read_bytes()).hexdigest()},
                         'opened_products': {}, 'raw': {}}
            with patch.object(frozen, 'ROOT', root), patch.object(frozen, 'inventory', return_value=inventory), \
                    patch.object(frozen.legacy, 'relative', side_effect=lambda p: p.relative_to(root).as_posix()):
                frozen.create(design, {'version': 'synthetic'}, [], metadata={'planned': 1})
                with self.assertRaisesRegex(RuntimeError, 'refusing overwrite'):
                    frozen.create(design, {}, [], metadata={})
                blobs = {'module.py': source.read_bytes(), 'design.json': design.read_bytes()}
                with patch.object(frozen.subprocess, 'check_output', side_effect=lambda args, **kw: blobs[args[2].split(':', 1)[1]]):
                    self.assertEqual(frozen.verify(design, {'version': 'synthetic'}, [], 'a'*40)['metadata']['planned'], 1)
                    blobs['module.py'] = b'changed source'
                    with self.assertRaisesRegex(RuntimeError, 'Git bytes differ'):
                        frozen.verify(design, {'version': 'synthetic'}, [], 'a'*40)
                with self.assertRaisesRegex(RuntimeError, 'design/source/input'):
                    frozen.verify(design, {'version': 'different'}, [], 'a'*40)

    def test_bad_commit_refused_before_loading(self):
        for value in ('a', 'A'*40, None, 'x'*40):
            with self.assertRaisesRegex(RuntimeError, '40-character'):
                frozen.verify(Path('absent'), {}, [], value)

    def test_runtime_requires_requests_and_preserves_pinned_packages(self):
        with patch.object(frozen.legacy, 'execution_runtime', return_value={'packages': {'numpy': 'pinned'}}):
            with patch.dict(frozen.os.environ, {name: '1' for name in frozen.THREAD_ENV}):
                result = frozen.runtime()
                self.assertEqual(result['packages'], {'numpy': 'pinned'})
                self.assertIn('not independently measured', result['thread_qualification'])
            with patch.dict(frozen.os.environ, {name: '2' for name in frozen.THREAD_ENV}):
                with self.assertRaisesRegex(RuntimeError, 'fresh CLI'):
                    frozen.runtime()


if __name__ == '__main__':
    unittest.main()
