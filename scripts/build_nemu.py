#!/usr/bin/env python3
"""Build pinned nemu-link variants in an already initialized West workspace."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import subprocess
import yaml

parser = argparse.ArgumentParser()
parser.add_argument('--workspace', type=Path, required=True)
parser.add_argument('--target', default='all')
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
repo = Path(__file__).resolve().parents[1]
workspace = args.workspace.resolve()
rows = yaml.safe_load((repo / 'build-nemu.yaml').read_text())['include']
selected = [r for r in rows if args.target in ('all', r['artifact-name'])]
if not selected:
    parser.error('Unknown target')
args.output.mkdir(parents=True, exist_ok=True)
# Resolve every module from this workspace; reject stale direct dependencies.
manifest = yaml.safe_load((repo / 'nemu/west.yml').read_text())['manifest']
for project in manifest['projects']:
    path = workspace / project.get('path', project['name'])
    actual = subprocess.check_output(['git', '-C', str(path), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != project['revision']:
        raise RuntimeError(f"Wrong revision for {project['name']}: {actual}")
    if subprocess.check_output(['git', '-C', str(path), 'status', '--porcelain'], text=True):
        raise RuntimeError(f"Modified dependency: {project['name']}")
source = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
dirty = bool(subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain'], text=True))
for row in selected:
    name = row['artifact-name']
    build = workspace / 'build' / name
    command = ['west', 'build', '-p', 'always', '-s', str(workspace / 'zmk/app'), '-d', str(build), '-b', row['board']]
    for snippet in row['snippet'].split():
        command += ['-S', snippet]
    command += ['--', f'-DZephyr_DIR={workspace / "zephyr/share/zephyr-package/cmake"}', f'-DZMK_CONFIG={repo / "config"}', f'-DZMK_EXTRA_MODULES={repo}', f'-DSHIELD={row["shield"]}']
    subprocess.run(command, cwd=workspace, env={**os.environ, "ZEPHYR_BASE": str(workspace / "zephyr"), "PYTHONDONTWRITEBYTECODE": "1"}, check=True)
    subprocess.run([sys.executable, str(repo/'scripts/verify_nemu_builds.py'), str(workspace), '--target', name], check=True)
    image = build / 'zephyr/zmk.uf2'
    data = image.read_bytes()
    if not data or len(data) % 512 or data[:8] != bytes.fromhex('5546320a57515d9e'):
        raise RuntimeError(f'Invalid UF2: {image}')
    dest = args.output / f'{name}.uf2'
    shutil.copyfile(image, dest)
    proof = dict(source=dict(commit=source, dirty=dirty), target=row,
                 sha256=hashlib.sha256(data).hexdigest(), manifest_sha256=hashlib.sha256((repo/'nemu/west.yml').read_bytes()).hexdigest())
    dest.with_suffix('.uf2.json').write_text(json.dumps(proof, indent=2)+'\n')
