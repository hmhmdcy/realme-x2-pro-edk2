#!/usr/bin/env python3
"""Verify the captured failed pixel probe; do not promote exit zero to success."""
import hashlib
import json
from pathlib import Path
import re
import tarfile

private = Path('/mnt/e/edk2-samurai-out/kernel131')
path = private / 'single-pixel-private.tar.gz'
assert hashlib.sha256(path.read_bytes()).hexdigest() == Path(str(path) + '.sha256').read_text().split()[0]
with tarfile.open(path) as archive:
    members = {m.name.removeprefix('./'): archive.extractfile(m).read()
               for m in archive.getmembers() if m.isfile()}
manifest = members['SHA256SUMS'].decode().splitlines()
for entry in manifest:
    expected, name = entry.split('  ', 1)
    name = name.removeprefix('./')
    assert hashlib.sha256(members[name]).hexdigest() == expected, name
assert len(manifest) == len(members) - 1
log = members['validation-private.txt'].decode()
assert log.count('Validation: Failure') == 1
assert 'Validation: Success' not in log
assert 'Expected: 0xffa7a7a7 Actual: 0xffa5a5a5 Distance: 3.464102' in log
assert 'GL_RENDERER:    FD640' in log
assert 'GL_VERSION:     OpenGL ES 3.2 Mesa 26.2.4' in log
assert members['validation-exit.txt'].strip() == b'0'
assert members['taint-samples.txt'].decode().split() == ['0'] * 7
assert members['phosh-before.txt'] == members['phosh-after.txt']
assert members['phoc-before.txt'] == members['phoc-after.txt']
assert not members['remaining-processes.txt']
assert not any(name.endswith('-private.data') for name in members)
before = members['dmesg-before.txt'].decode().splitlines()
after = members['dmesg-delayed.txt'].decode().splitlines()
assert after[:len(before)] == before
delta = after[len(before):]
fault = re.compile(r'gpu.*fault|FAULT.*gpu|CCU.*TRANSLATION|CP.*FAULT', re.I)
assert not any(fault.search(line) for line in delta)
for name in ['package-db-prepared-check.txt', 'package-db-final-check.txt',
             'nv-check.txt', 'source-check.txt', 'vendor-check.txt', 'binary-check.txt']:
    lines = members[name].decode().splitlines()
    assert lines and all(line.endswith(': OK') for line in lines), name
assert members['radio-audio.txt'].decode().split() == ['running', 'running']
assert 'started' in members['bluetooth-service.txt'].decode()
samples = [float(line.split()[1]) for line in members['samples.txt'].decode().splitlines()]
assert len(samples) == 7 and samples[-1] - samples[0] >= 30
result = dict(archive_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
              verified_members=len(manifest), kernel=129,
              renderer='FD640', mesa='26.2.4', scene='build:use-vbo=true',
              surface='1080x2259', expected='0xffa7a7a7', actual='0xffa5a5a5',
              rgb_delta_per_channel=2, distance=3.464102,
              pixel_validation='FAIL', process_exit=0,
              delayed_observation_seconds=round(samples[-1] - samples[0], 3),
              new_gpu_fault_lines=0, devcoredumps=0, taint_samples=7,
              desktop_pids_unchanged=True, package_nv_sources_checks=True,
              full_gpu_acceptance=False)
public = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel131/single-pixel-validation.json')
public.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
