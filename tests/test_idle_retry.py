"""Exercise the compiled-in idle wake function against scripted radio results."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class IdleRetry(unittest.TestCase):
    def test_wake_and_backoff(self):
        module = os.environ.get("NEMU_MODULE_DIR")
        if not module:
            self.skipTest("set NEMU_MODULE_DIR to the pinned module")
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            patched = tmp / "link.c"
            subprocess.run([sys.executable, ROOT / "scripts/patch_nemu_shared_settings.py",
                            Path(module) / "src/link/link_esb.c", patched], check=True)
            code = patched.read_text().split("int idle_wake(void) {", 1)[1].split("\n}", 1)[0]
            fixture = (ROOT / "tests/idle_wake_fixture.c").read_text()
            (tmp / "test.c").write_text(fixture.replace("/* WAKE */", "int idle_wake(void) {" + code + "\n}"))
            subprocess.run(["cc", "-std=c11", "-Werror", tmp / "test.c", "-o", tmp / "test"], check=True)
            subprocess.run([tmp / "test"], check=True)
