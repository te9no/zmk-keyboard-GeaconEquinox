import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ModeRecoveryTest(unittest.TestCase):
    def test_transition_failures_and_retry(self):
        module = os.environ.get("NEMU_MODULE_DIR")
        if not module:
            self.skipTest("set NEMU_MODULE_DIR to the pinned nemu-link module")
        original = Path(module) / "src/mode/link_mode_switch.c"
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            patched = work / "patched.c"
            subprocess.run(["patch", "--batch", "--fuzz=0", "-o", patched, original,
                            "-i", ROOT / "scripts/nemu_mode_recovery.patch"], check=True)
            src = patched.read_text()
            runtime = src[src.index("bool zmk_nemu_link_owns_radio"):src.index("int zmk_nemu_link_request_mode")]
            fixture = (ROOT / "tests/mode_recovery_fixture.c").read_text()
            (work / "test.c").write_text(fixture.replace("/* MODE_IMPLEMENTATION */", runtime))
            subprocess.run(["cc", "-std=c11", "-Werror", str(work / "test.c"), "-o",
                            str(work / "test")], check=True)
            subprocess.run([work / "test"], check=True)
