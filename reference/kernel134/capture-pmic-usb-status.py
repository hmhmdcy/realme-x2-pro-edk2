#!/usr/bin/env python3
"""Fixed, individually sought PM8150B status reads; no full register dump."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import time

out = Path('/var/lib/samurai/k134-pmic-usb-status')
regmap = Path('/sys/kernel/debug/regmap/0-02')
pmic = Path('/sys/bus/spmi/devices/0-02')
expected_of = Path('/sys/firmware/devicetree/base/soc@0/spmi@c440000/pmic@2')
boot = Path('/proc/sys/kernel/random/boot_id').read_text()
assert os.geteuid() == 0 and os.uname().release == '7.3.0-rc6-rmx1931-samurai-k132+'
assert boot == Path('/var/lib/samurai/k132-first-runtime/boot-id-private.txt').read_text()
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
assert pmic.joinpath('of_node').resolve() == expected_of
assert b'qcom,pm8150b\0' in expected_of.joinpath('compatible').read_bytes()
assert regmap.joinpath('name').read_text().strip() == 'pmic-spmi'
# This metadata-only range read builds/verifies the printable-offset cache.
# The matching kernel config has reg_bits16, val_bits8, stride1, max0xffff,
# no readable/precious callbacks. One record is exactly nine bytes.
assert regmap.joinpath('range').read_text() == '0-ffff\n'
assert not out.exists()
out.mkdir(mode=0o700)
(out / 'boot-id-private.txt').write_text(boot)

def capture(args, name, timeout=60):
    with (out / name).open('x') as log:
        subprocess.run(args, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=timeout)

capture(['dmesg'], 'dmesg-before-private.txt')
capture(['sha256sum', '/etc/apk/world', '/lib/apk/db/installed'], 'package-before.sha256')
for name in ['phosh', 'phoc']:
    capture(['pgrep', '-x', name], name + '-before.txt')
capture(['cat', '/sys/class/power_supply/mp2650-input/uevent'], 'charger-before.txt')
gadget = Path('/sys/kernel/config/usb_gadget/samurai/configs/c.1')
udc = Path('/sys/class/udc/a600000.usb')
usb = {name: gadget.joinpath(name).read_text().strip() for name in ['MaxPower', 'bmAttributes']}
usb.update({name: udc.joinpath(name).read_text().strip() for name in ['state', 'current_speed']})
assert usb['state'] == 'configured'
(out / 'usb-state.json').write_text(json.dumps(usb, indent=2) + '\n')
registers = (0x1307, 0x1308, 0x1310, 0x1506, 0x1509, 0x150b, 0x150d)
samples = []
fd = os.open(regmap / 'registers', os.O_RDONLY | os.O_CLOEXEC)
try:
    for index in range(8):
        values = {}
        for register in registers:
            line = os.pread(fd, 9, register * 9)
            match = re.fullmatch(rb'([0-9a-f]{4}): ([0-9a-f]{2})\n', line)
            assert match and int(match[1], 16) == register, (register, line)
            values[f'0x{register:04x}'] = int(match[2], 16)
        samples.append(dict(index=index, monotonic=time.monotonic(), registers=values))
        if index != 7:
            time.sleep(0.25)
finally:
    os.close(fd)
(out / 'status-samples.json').write_text(json.dumps(samples, indent=2) + '\n')
for name, manifest in [('nv', '/run/samurai-wifi/nv-source-hashes.txt'),
                       ('source', '/var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256'),
                       ('vendor', '/var/lib/samurai/k115-vendor-camera-source/vendor-before.sha256'),
                       ('package', str(out / 'package-before.sha256'))]:
    capture(['sha256sum', '-c', manifest], name + '-check.txt')
for name in ['phosh', 'phoc']:
    capture(['pgrep', '-x', name], name + '-after.txt')
    assert (out / (name + '-before.txt')).read_text() == (out / (name + '-after.txt')).read_text()
capture(['cat', '/sys/class/power_supply/mp2650-input/uevent'], 'charger-after.txt')
capture(['dmesg'], 'dmesg-after-private.txt')
assert boot == Path('/proc/sys/kernel/random/boot_id').read_text()
assert udc.joinpath('state').read_text().strip() == 'configured'
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
(out / 'operation-validation.json').write_text(json.dumps(dict(status_register_reads=56, register_data_writes=0,
    whole_register_dump=False, typec_role_or_pd_changes=0, client_or_driver_rebinding=0,
    same_boot=True, same_desktop_pids=True, taint=0, usb_remained_configured=True), indent=2) + '\n')
(out / 'SHA256SUMS').write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ./' + p.name
    for p in sorted(out.iterdir()) if p.is_file()) + '\n')
assert not Path('/tmp/k134-pmic-usb-status-private.tar.gz').exists()
subprocess.run(['tar', '-C', str(out), '-czf', '/tmp/k134-pmic-usb-status-private.tar.gz', '.'], check=True, timeout=20)
print('K134_FIXED_PMIC_STATUS_READS_COMPLETE_USB_UNCHANGED', flush=True)
