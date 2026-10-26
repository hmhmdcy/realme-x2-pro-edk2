from pathlib import Path
import hashlib
import json
import re
import sys
import tarfile

r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel136'
out = Path('/mnt/e/edk2-samurai-out/kernel136')

def load(path):
    with tarfile.open(path) as archive:
        data = {m.name.removeprefix('./'): archive.extractfile(m).read()
                for m in archive if m.isfile()}
    if 'SHA256SUMS' in data:
        for line in data['SHA256SUMS'].decode().splitlines():
            digest, name = line.split('  ', 1)
            assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest() == digest
    return data

data = load(out / 'first-runtime-private.tar.gz')
before = load(out / 'preflash-private.tar.gz')
assert data['boot-id-private.txt'] != before['boot-id-private.txt']
assert b'#136 SMP' in data['uname.txt']
assert b'7.3.0-rc6-rmx1931-samurai-k132+' in data['uname.txt']
taint = int(data['state.txt'].splitlines()[-1])
assert data['console-node.txt'].strip() == b'character special file 600 5 1 0 0'
for name, count in [('nv-check.txt', 6), ('source-check.txt', 4), ('vendor-check.txt', 1),
                    ('full-module-check.txt', 784), ('gui-config-check.txt', 3)]:
    assert data[name].count(b': OK') == count and b'FAILED' not in data[name]
old = load(out.parent / 'kernel112/layout-after.tar')
for dev in ['sda', 'sdb', 'sdc', 'sdd', 'sde', 'sdf']:
    for suffix in ['geometry', 'head', 'tail']:
        assert data[dev + '.' + suffix] == old[dev + '.' + suffix]
parts = {name: digest for digest, name in
         (line.split('  ', 1) for line in data['partition-check.sha256'].decode().splitlines())}
bundle = json.loads((ref / 'trace-build-package-validation.json').read_text())
assert parts['/dev/sde11'] == bundle['artifacts'][0]['sha256']
assert parts['/dev/sde32'] == bundle['artifacts'][1]['sha256']
assert parts['/dev/sda2'] == '7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'
sys.path.insert(0, str(r / 'reference/kernel113'))
from inspect_live_fdt import fdt
expected = fdt((out.parent / 'kernel132/DTB-k132-private').read_bytes())
live = fdt(data['live-fdt-private.dtb'])
assert live.keys() == expected.keys()
for name, props in expected.items():
    assert all(live[name].get(key) == value for key, value in props.items())
assert data['vm-events-default.txt'].splitlines() == [b'0', b'0']
for name in ['vm-update-format.txt', 'vm-switch-format.txt']:
    assert b'field:u64 ttbr' in data[name]
(out / 'embedded-boot-id-private.txt').write_bytes(data['boot-id-private.txt'])
dmesg = data['dmesg.txt'].decode()
counts = {name: len(re.findall(pattern, dmesg)) for name, pattern in [
    ('gpu_faults', r'gpu fault:'), ('dpu_timeouts', r'frame done timeout'),
    ('dsi_errors', r'dsi_err_worker'), ('kernel_warns', r'WARNING:'),
    ('codec_enospc', r'Failed to read.*-28')]}
report = dict(stage=136, kernel_build=136, software_generation=132,
              new_boot_verified=True, boot132_and_logdump136_readback_exact=True,
              persist_preserved=True, gpt18_preserved=True,
              nv6_source4_vendor1_preserved=True, all_770_modules_verified=True,
              actual_live_dtb_matches132=True, taint=taint, console_correct=True,
              phosh_present=bool(data['phosh.txt'].strip()),
              phoc_present=bool(data['phoc.txt'].strip()),
              new_tracepoints_present_and_default_disabled=True,
              drm_crtc_active=b'active=1' in data['drm-state.txt'],
              charging_control_accepted=False, counts=counts,
              clean_runtime_accepted=taint == 0 and not any(counts.values()),
              gpu_probe_allowed=taint == 0 and counts['gpu_faults'] == 0,
              goal_complete=False)
(ref / 'first-runtime-validation.json').write_text(json.dumps(report, indent=2) + '\n')
(out / 'first-runtime-validation.json').write_text(json.dumps(report, indent=2) + '\n')
bundle['deployed'] = True
bundle['actual_runtime_verified'] = True
(ref / 'trace-build-package-validation.json').write_text(json.dumps(bundle, indent=2) + '\n')
print(json.dumps(report, indent=2))
