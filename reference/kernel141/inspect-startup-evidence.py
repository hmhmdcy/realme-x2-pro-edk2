from pathlib import Path
import hashlib
import json
import re
import tarfile

r = Path('/mnt/e/RealmeX2Pro edk2')
out = Path('/mnt/e/edk2-samurai-out/kernel141')
ref = r / 'reference/kernel141'
assert not out.exists()
out.mkdir(mode=0o700)

def load(path):
    with tarfile.open(path) as archive:
        data = {m.name.removeprefix('./'): archive.extractfile(m).read() for m in archive if m.isfile()}
    for line in data['SHA256SUMS'].decode().splitlines():
        digest, name = line.split('  ', 1)
        assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest() == digest
    return data

first = load(out.parent / 'kernel140/first-runtime-private.tar.gz')
settled = load(out.parent / 'kernel140/settled-health-private.tar.gz')
assert first['boot-id-private.txt'] == settled['boot-id-private.txt']
d = settled['dmesg-final-private.txt'].decode()
timeout_rows = []
for line in d.splitlines():
    if 'frame done timeout' in line:
        stamp = float(re.match(r'\[\s*([0-9.]+)\]', line).group(1))
        m = re.search(r'frame done timeout[^\n]*', line)
        timeout_rows.append(dict(dmesg_seconds=stamp, message=re.sub(r'\b[0-9a-f]{8,16}\b', '[redacted]', m.group())))
assert len(timeout_rows) == 4
report = dict(stage=141, source_boot=140, source_archives_hash_verified=True,
              same_boot=True, previous_goal_turn='progress',
              previous_turn_reason='two kernels deployed; actual-function error-path injection and live evidence change next action',
              startup_dpu_timeouts=timeout_rows, initial_trace_instances=first['traces.txt'].decode().splitlines(),
              initial_phosh_present=bool(first['phosh.txt'].strip()),
              initial_phoc_present=bool(first['phoc.txt'].strip()),
              cross_clock_order_not_assumed=True, display_fix_not_yet_proven=True, goal_complete=False)
(ref / 'startup-evidence-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
