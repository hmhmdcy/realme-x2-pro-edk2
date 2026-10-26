#!/usr/bin/env python3
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import runpy
import subprocess
import time

runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel118/ensure-build-volume.py')
root = Path('/home/cy122/pmos-samurai-kernel118/mesa-offline')
out = Path('/mnt/e/edk2-samurai-out/kernel131/gpu-coredump')
public = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel131')
binary = root / 'decode-build/src/freedreno/decode/crashdec'
assert hashlib.sha256(binary.read_bytes()).hexdigest() == '4a68706bad1d03366196327dd0ebf2294910fd73fad93fdbabdf19d43d2c4b3b'
core = out / 'devcd1-private.data'
assert hashlib.sha256(core.read_bytes()).hexdigest() == '344ea161e585686ee02ab2557c9021de416fef1a0bcda7fbb282cc089c5a5d18'

def limits():
    resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (40, 40))
    resource.setrlimit(resource.RLIMIT_FSIZE, (32 * 1024**2, 32 * 1024**2))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

logfile = out / 'decoded-summary-private.txt'
assert not logfile.exists()
env = dict(os.environ, RNN_PATH=str(root / 'mesa-26.2.4/src/freedreno/registers'),
           GALLIUM_DUMP_CPU='false', TMPDIR=str(root))
start = time.monotonic()
with logfile.open('w') as log:
    try:
        process = subprocess.run([str(binary), '-s', '-f', str(core)], stdout=log,
                                 stderr=subprocess.STDOUT, env=env, cwd=root,
                                 preexec_fn=limits, timeout=50)
        code = process.returncode
    except subprocess.TimeoutExpired:
        code = 'timeout'
decoded = logfile.read_text(errors='replace')
raw = core.read_text(errors='replace')
report = dict(mesa='26.2.4', decoder_exit=code,
              wall_seconds=round(time.monotonic() - start, 2),
              decoded_bytes=logfile.stat().st_size,
              decoded_sha256=hashlib.sha256(logfile.read_bytes()).hexdigest(),
              raw_addresses_private=True, driver_fault_unresolved=True,
              root_cause_proven=False)
fault = re.search(r'^fault-info:\n(.*?)(?=^[a-z])', raw, re.S | re.M)
pg = re.search(r'^pgtable-fault-info:\n(.*?)(?=^[a-z])', raw, re.S | re.M)
bos_section = re.search(r'^bos:\n(.*?)(?=^[a-z])', raw, re.S | re.M)
if fault and pg and bos_section:
    iova = int(re.search(r'iova=(?:0x)?([0-9a-fA-F]+)', fault[1])[1], 16)
    bos = [(int(m[1], 16), int(m[2])) for m in re.finditer(r'  - iova: ((?:0x)?[0-9a-fA-F]+)\n    size: ([0-9]+)', bos_section[1])]
    ptes = [int(value, 16) for value in re.search(r'ptes: (.*)', pg[1])[1].split()]
    report.update(captured_buffer_objects=len(bos), fault_in_listed_bo=any(base <= iova < base + size for base, size in bos),
                  zero_page_table_descriptors=sum(value == 0 for value in ptes),
                  fault_and_page_table_ttbr_match=int(re.search(r'ttbr0=(?:0x)?([0-9a-fA-F]+)', fault[1])[1], 16) == int(re.search(r'ttbr0: (?:0x)?([0-9a-fA-F]+)', pg[1])[1], 16),
                  vm_history_present=bool(re.search(r'^vm-log:', raw, re.M)),
                  bo_list_is_not_proven_complete_address_space=True)
lines = decoded.splitlines()
index = next((i for i, line in enumerate(lines) if 'ESTIMATED CRASH LOCATION' in line), None)
report['estimated_location_found'] = index is not None
if index is not None:
    report['estimated_preceding_commands'] = list(dict.fromkeys(re.findall(r'\bCP_[A-Z0-9_]+\b', '\n'.join(lines[max(0, index - 10):index]))))
    report['estimated_following_commands'] = list(dict.fromkeys(re.findall(r'\bCP_[A-Z0-9_]+\b', '\n'.join(lines[index + 1:index + 10]))))
(public / 'core-decode-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
subprocess.run(['sync'], check=True)
subprocess.run(['umount', '/home/cy122/pmos-samurai-kernel118'], check=True)
print('UNCHANGED_K118_DECODE_VOLUME_UNMOUNTED')
