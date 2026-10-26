from pathlib import Path
import hashlib
import json
import re
import sys
import tarfile

r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel137'
out = Path('/mnt/e/edk2-samurai-out/kernel137')
def load(path):
    with tarfile.open(path) as archive:
        data = {m.name.removeprefix('./'): archive.extractfile(m).read() for m in archive if m.isfile()}
    if 'SHA256SUMS' in data:
        for line in data['SHA256SUMS'].decode().splitlines():
            digest, name = line.split('  ', 1)
            assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest() == digest
    return data
data = load(out / 'preflash-private.tar.gz')
old136 = load(out.parent / 'kernel136/first-runtime-private.tar.gz')
assert data['boot-id-private.txt'] == old136['boot-id-private.txt']
assert b'#136 SMP' in data['uname.txt']
assert data['state.txt'].splitlines()[-1] == b'512'
for name, count in [('nv-check.txt', 6), ('source-check.txt', 4), ('vendor-check.txt', 1), ('full-module-check.txt', 784), ('gui-config-check.txt', 3)]:
    assert data[name].count(b': OK') == count and b'FAILED' not in data[name]
layout = load(out.parent / 'kernel112/layout-after.tar')
for dev in ['sda', 'sdb', 'sdc', 'sdd', 'sde', 'sdf']:
    for suffix in ['geometry', 'head', 'tail']:
        assert data[dev + '.' + suffix] == layout[dev + '.' + suffix]
assert data['partition-check.sha256'] == old136['partition-check.sha256']
assert data['phosh.txt'].strip() and data['phoc.txt'].strip()
assert data['vm-events-default.txt'].splitlines() == [b'0', b'0']
sys.path.insert(0, str(r / 'reference/kernel113'))
from inspect_live_fdt import fdt
assert fdt(data['live-fdt-private.dtb']) == fdt(old136['live-fdt-private.dtb'])
dmesg = data['dmesg.txt'].decode()
counts = dict(gpu_faults=dmesg.count('gpu fault:'), kernel_warnings=dmesg.count('WARNING:'),
              dma_tx_prepare_failures=dmesg.count('unable to prepare channel'),
              codec_enospc=len(re.findall(r'Failed to read.*-28', dmesg)))
assert counts == dict(gpu_faults=2, kernel_warnings=1, dma_tx_prepare_failures=31, codec_enospc=0), counts
(out / 'source-boot-id-private.txt').write_bytes(data['boot-id-private.txt'])
report = dict(stage=137, current_kernel=136, current_boot_verified=True,
    preflash_audit_pass=True, compatibility132_preserved=True, phosh_present=True, phoc_present=True,
    gpt18_preserved=True, persist_preserved=True, nv6_source4_vendor1_preserved=True,
    all_770_modules_verified=True, actual_live_dtb_matches132=True,
    taint=512, known_wcd_warning_diagnostic_boot=True, counts=counts,
    clean_runtime_accepted=False, goal_complete=False)
(ref / 'preflash-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('K137_CURRENT136_PREFLASH_GUARDS_PASS_PREEXISTING_FAILURES_RECORDED', flush=True)
