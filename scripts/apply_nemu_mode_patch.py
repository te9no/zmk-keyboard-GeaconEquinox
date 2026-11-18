"""Apply the release-pinned diff to a private copy using the build image's Git."""
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

source, delta, output = (Path(arg).resolve() for arg in sys.argv[1:])
with TemporaryDirectory() as temp:
    copy = Path(temp) / "link_mode_switch.c"
    shutil.copyfile(source, copy)
    subprocess.run(["git", "apply", str(delta)], cwd=temp, check=True)
    shutil.copyfile(copy, output)
