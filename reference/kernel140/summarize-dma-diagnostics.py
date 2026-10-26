from pathlib import Path
import hashlib
import json
import re
import tarfile

r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel140'
out = Path('/mnt/e/edk2-samurai-out/kernel140')
with tarfile.open(out / 'first-health-private.tar.gz') as archive:
    data = {m.name.removeprefix('./'): archive.extractfile(m).read() for m in archive if m.isfile()}
for line in data['SHA256SUMS'].decode().splitlines():
    digest, name = line.split('  ', 1)
    assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest() == digest
assert data['boot-id-private.txt'] == (out / 'embedded-boot-id-private.txt').read_bytes()
d = data['dmesg-final-private.txt'].decode()
patterns = {
    'tx_first_failure': r'TX DMA diagnostic: state=(\d+) qmi=(\d+) channel=(\d+) device=(\d+) sg=(\d+) config_sg=(\d+) len=(\d+)',
    'suspend_first_rejection': r'NGD suspend rejected: ret=(-?\d+) state=(\d+) tx_channel=(\d+) rx_channel=(\d+)',
    'bam_first_allocation_failure': r'BAM DMA diagnostic: allocation failed count=(\d+) sg_len=(\d+) len=(\d+) direction=(\d+)'}
names = {'tx_first_failure': ['state', 'qmi', 'channel', 'device', 'sg', 'config_sg', 'len'],
         'suspend_first_rejection': ['ret', 'state', 'tx_channel', 'rx_channel'],
         'bam_first_allocation_failure': ['count', 'sg_len', 'len', 'direction']}
records = {}
for name, pattern in patterns.items():
    hits = []
    for line in d.splitlines():
        m = re.search(pattern, line)
        if m:
            fields = dict(zip(names[name], map(int, m.groups())))
            fields['dmesg_seconds'] = float(re.match(r'\[\s*([0-9.]+)\]', line).group(1))
            hits.append(fields)
    assert len(hits) <= 1, name
    records[name] = hits[0] if hits else None
tx = records['tx_first_failure']
susp = records['suspend_first_rejection']
chain = bool(tx and susp and tx['channel'] == 0 and susp['ret'] == -16 and susp['tx_channel'] == 0 and susp['dmesg_seconds'] < tx['dmesg_seconds'])
health = json.loads(data['health-validation.json'])
assert health['stage'] == 140 and health['current_kernel'] == 140
health['archive_hash_verified'] = True
(ref / 'first-health-validation.json').write_text(json.dumps(health, indent=2) + '\n')
report = dict(stage=140, current_kernel=140, same_boot_verified=True,
              archive_hash_verified=True, diagnostics=records,
              first_prepare_failure_has_null_channel=bool(tx and tx['channel'] == 0),
              first_prepare_failure_is_bam_allocation_failure=bool(tx and tx['channel'] and records['bam_first_allocation_failure']),
              rejected_suspend_before_null_channel_observed=chain,
              exact_intervening_all_events_not_traced=True,
              no_allocation_policy_or_suspend_order_changed=True,
              functional_fix_of_null_channel_not_yet_applied=True,
              goal_complete=False)
(ref / 'dma-first-failure-validation.json').write_text(json.dumps(report, indent=2) + '\n')
runtime = json.loads((ref / 'first-runtime-validation.json').read_text())
runtime['gpu_probe_allowed'] = False
runtime['final_health_record'] = 'first-health-validation.json'
runtime['initial_desktop_snapshot_precedes_final_health'] = True
(ref / 'first-runtime-validation.json').write_text(json.dumps(runtime, indent=2) + '\n')
print(json.dumps(report, indent=2))
print(json.dumps(health, indent=2))
