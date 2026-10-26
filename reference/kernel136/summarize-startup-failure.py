from pathlib import Path
import hashlib
import json
import re
import tarfile

out = Path('/mnt/e/edk2-samurai-out/kernel136')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel136')
with tarfile.open(out / 'first-runtime-private.tar.gz') as archive:
    d = {m.name.removeprefix('./'): archive.extractfile(m).read()
         for m in archive if m.isfile()}
t = d['dmesg.txt'].decode()
lines = t.splitlines()
for n, line in enumerate(lines):
    if 'Efuse sense' in line:
        (out / 'efuse-warning-context-private.txt').write_text('\n'.join(lines[max(0,n-35):n+40]))
errors = ['unable to prepare channel', 'Unable to prepare rx channel',
          'Sanity check failed', 'ctrl wrong state', 'failed:-22',
          'failed:-28', 'Got response to invalid TID', 'Error allocating slim regmap']
report = dict(stage=136, warning='wcd934x_enable_efuse_sensing',
              status_value=0, register_read_return=-22,
              error_counts={s:t.count(s) for s in errors},
              first_tx_error_seconds=None, efuse_warning_seconds=None,
              mfd_cleanup_absent=True, cleanup_proven_to_fix_this_warning=False,
              gpu_probe_not_run_on_this_boot=True, goal_complete=False)
for field, needle in [('first_tx_error_seconds','unable to prepare channel'),
                       ('efuse_warning_seconds','Efuse sense')]:
    match = next((re.search(r'^\[\s*([0-9.]+)\]', s) for s in lines if needle in s), None)
    if match:
        report[field] = float(match[1])
(ref / 'startup-failure-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
