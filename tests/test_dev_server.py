"""Verify the actual direct-script and module launch paths after API imports."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LauncherTests(unittest.TestCase):
    def launch(self, args, cwd):
        result = subprocess.run([sys.executable, "-B", *args, "--check"], cwd=cwd,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn("API imports OK: observations, frame",result.stdout)

    def test_module_entrypoint(self):
        self.launch(["-m", "scripts.serve_app"],ROOT)

    def test_direct_script_entrypoint_from_another_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            self.launch([str(ROOT / "scripts/serve_app.py")],temp)
