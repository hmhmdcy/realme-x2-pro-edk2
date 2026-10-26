#!/usr/bin/env python3
"""Fetch hash-locked public sources and build the RAM work-file TFTP server."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request, urlopen
import argparse, hashlib, json, subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--work-dir', type=Path, required=True)
parser.add_argument('--source-cache', type=Path, help='Optional previously downloaded, hash-verified source tree')
args = parser.parse_args()
here = Path(__file__).resolve().parent
lock = json.loads((here / 'source-lock.json').read_text())
assert not lock['unresolved_optional_source_paths']
for name, digest in lock['own_sources'].items():
    assert hashlib.sha256((here / name).read_bytes()).hexdigest() == digest, name
work = args.work_dir.resolve()
work.mkdir(mode=0o700)
def fetch(record):
    project = record['repo'].split('/')[-1]
    target = work / project / record['path']
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    url = 'https://raw.githubusercontent.com/' + record['repo'] + '/' + record['commit'] + '/' + record['path']
    if args.source_cache is not None:
        data = (args.source_cache / project / record['path']).read_bytes()
    else:
        with urlopen(Request(url, headers={'User-Agent': 'samurai-linux-build'}), timeout=40) as response:
            data = response.read(2_000_000)
    assert len(data) == record['bytes'] and hashlib.sha256(data).hexdigest() == record['sha256'], record['path']
    target.write_bytes(data)
with ThreadPoolExecutor(max_workers=4) as pool:
    list(pool.map(fetch, lock['source_records']))
def command(command, label, cwd=None):
    p = subprocess.run(command, capture_output=True, cwd=cwd)
    (work / (label + '.log')).write_bytes(p.stdout + p.stderr)
    assert p.returncode == 0, label
    return p
command(['patch', '--fuzz=0', '-p1', '-i', str(here / 'tqftpserv-work-files.patch')], 'patch', work / 'tqftpserv')
patched = work / 'tqftpserv/tqftpserv.c'
assert hashlib.sha256(patched.read_bytes()).hexdigest() == lock['patched_server_source_sha256']
binary = work / 'samurai-tqftpserv'
result = command(['aarch64-linux-gnu-gcc', '-D_GNU_SOURCE', '-O2', '-Wall', '-Wextra', '-Werror', '-static', '-I' + str(work / 'qrtr/include'), '-I' + str(work / 'tqftpserv'), str(patched), str(here / 'samurai-tftp-ram.c'), str(work / 'qrtr/lib/qrtr.c'), str(work / 'qrtr/lib/logging.c'), str(here / 'ro-firmware.c'), '-o', str(binary)], 'build')
assert not result.stderr
report = dict(pinned_source_files=len(lock['source_records']), all_source_hashes_verified=True, verified_source_cache_used=args.source_cache is not None, patch_applied_without_fuzz=True, patched_source_exact=True, compiler_warnings=0, candidate_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(), candidate_bytes=binary.stat().st_size)
(work / 'build-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
