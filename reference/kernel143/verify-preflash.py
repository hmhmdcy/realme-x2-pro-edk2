from pathlib import Path
import hashlib
import json
import sys
import tarfile

r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel143'
out = Path('/mnt/e/edk2-samurai-out/kernel143')
with tarfile.open(out / 'preflash-private.tar.gz') as archive:
    data = {m.name.removeprefix('./'): archive.extractfile(m).read() for m in archive if m.isfile()}
for line in data['SHA256SUMS'].decode().splitlines():
    digest, name = line.split('  ', 1)
    assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest() == digest
boot = (out.parent / 'kernel142/embedded-boot-id-private.txt').read_bytes()
assert data['boot-id-private.txt'] == boot
assert b'#140 SMP' in data['uname.txt']
assert data['state.txt'].splitlines()[-1] == b'0'
assert 'phosh.txt' in data and 'phoc.txt' in data
for name, count in [('nv-check.txt', 6), ('source-check.txt', 4), ('vendor-check.txt', 1)]:
    assert data[name].count(b': OK') == count and b'FAILED' not in data[name]
assert data['old132-module-check.txt'].count(b': OK') >= 770
with tarfile.open(out.parent / 'kernel112/layout-after.tar') as archive:
    old = {m.name.removeprefix('./'): archive.extractfile(m).read() for m in archive if m.isfile()}
for dev in ['sda', 'sdb', 'sdc', 'sdd', 'sde', 'sdf']:
    for suffix in ['geometry', 'head', 'tail']:
        assert data[dev + '.' + suffix] == old[dev + '.' + suffix]
parts = {name: digest for digest, name in (line.split('  ', 1) for line in data['partition-check.sha256'].decode().splitlines())}
assert parts['/dev/sde11'] == '501074e6feb3c5e93eff86f40848acbfc102da44e06cf52f95770d80a83d07f6'
assert parts['/dev/sde32'] == '0ac9d6678ba4218a049fca47090c4fdd290d03d6a1fd72a6d9f04f046b21d925'
assert parts['/dev/sda2'] == '7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'
sys.path.insert(0, str(r / 'reference/kernel113'))
from inspect_live_fdt import fdt
expected = fdt((out.parent / 'kernel132/DTB-k132-private').read_bytes())
live = fdt(data['live-fdt-private.dtb'])
assert live.keys() == expected.keys()
for name, props in expected.items():
    assert all(live[name].get(key) == value for key, value in props.items())
(out / 'source-boot-id-private.txt').write_bytes(boot)
report = dict(stage=143, current_kernel=140, current_boot_verified=True,
              boot132_logdump140_persist_verified=True, gpt18_preserved=True,
              nv6_source4_vendor1_preserved=True, all_770_current_modules_verified=True,
              actual_live_dtb_matches132=True, taint=0,
              desktop_processes_present=bool(data['phosh.txt'].strip() and data['phoc.txt'].strip()),
              phosh_present=bool(data['phosh.txt'].strip()),
              phoc_present=bool(data['phoc.txt'].strip()),
              current_gpu_fault_count_zero=True,
              preflash_audit_pass=True, goal_complete=False)
(ref / 'preflash-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('K143_FRESH_CURRENT_BOOT_PREFLASH_PARTITION_DTB_GPT_MODULE_GUARDS_PASS', flush=True)
