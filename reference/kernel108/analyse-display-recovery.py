#!/usr/bin/env python3
import hashlib
import json
import re
import tarfile
from pathlib import Path

root = Path('/mnt/e/edk2-samurai-out/kernel108')
with tarfile.open(root / 'display-recovery-once.tar') as archive:
    data = {Path(m.name).name: archive.extractfile(m).read().decode(errors='replace')
            for m in archive.getmembers() if m.isfile()}
start = float(data['uptime-after.txt'].split()[0])
samples = []
for seconds in (0, 10, 30, 60):
    lines = data[f'dmesg-{seconds}.txt'].splitlines()
    recent = []
    for line in lines:
        match = re.match(r'\[\s*([0-9.]+)\]', line)
        if match and float(match.group(1)) >= start and re.search(r'dsi_err_worker|frame.done.timeout|underflow|sofef03f.*power.mode', line, re.I):
            recent.append(line)
    samples.append({'seconds': seconds, 'uptime': data[f'uptime-{seconds}.txt'].strip(),
                    'encoder': data[f'encoder-{seconds}.txt'].strip(), 'display_errors_after_cycle': recent})
summary = {'kernel': 106, 'new_kernel_built': False, 'partitions_flashed': False,
           'cycle_exit': int(data['cycle-exit.txt']), 'samples': samples,
           'brightness': int(data['brightness-after.txt']), 'taint': int(data['taint-after.txt']),
           'wifi': data['wifi-status.txt'].splitlines(), 'remoteprocs': data['remoteprocs.txt'].splitlines(),
           'snapshot_preserved': data['snapshot-before.sha256'] == data['snapshot-after.sha256'],
           'cycle_log': data['kms-cycle.txt'].splitlines(),
           'original_archive_sha256': hashlib.sha256((root / 'display-recovery-once.tar').read_bytes()).hexdigest(),
           'optical_confirmation': 'pending', 'permanent_fix': False}
output = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel108/display-recovery-summary.json')
assert not output.exists()
output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n')
print(json.dumps(summary, indent=2, ensure_ascii=False))
