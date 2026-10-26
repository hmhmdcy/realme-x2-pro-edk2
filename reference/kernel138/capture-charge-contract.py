#!/usr/bin/env python3
from pathlib import Path
import hashlib
import json
import os
import subprocess
import time

out = Path('/var/lib/samurai/k138-charge-contract')
client = Path('/sys/bus/i2c/devices/0-005c')
driver = Path('/sys/bus/i2c/drivers/mp2650')
psy = Path('/sys/class/power_supply/mp2650-input')
reader = Path('/var/lib/samurai/k131-read-mp2650')
boot = Path('/proc/sys/kernel/random/boot_id').read_text()
assert os.geteuid() == 0 and os.uname().release == '7.3.0-rc6-rmx1931-samurai-k132+'
assert boot == Path('/var/lib/samurai/k137-rollback132-runtime/boot-id-private.txt').read_text()
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
assert client.joinpath('driver').resolve() == driver
assert client.joinpath('of_node').resolve() == Path('/sys/firmware/devicetree/base/soc@0/geniqup@8c0000/i2c@884000/charger@5c')
assert hashlib.sha256(reader.read_bytes()).hexdigest() == '6ef5467f5a445d718bd783ed86aabe5e93d08c442f483978355ad42ec79d5673'
assert not out.exists()
out.mkdir(mode=0o700)
(out / 'boot-id-private.txt').write_text(boot)
def capture(args, name, check=True, timeout=60):
    with (out / name).open('w') as log:
        return subprocess.run(args, stdout=log, stderr=subprocess.STDOUT, check=check, timeout=timeout).returncode
capture(['dmesg'], 'dmesg-before-private.txt')
capture(['sha256sum', '/etc/apk/world', '/lib/apk/db/installed'], 'package-db-before.sha256')
for name in ['phosh', 'phoc']:
    capture(['pgrep', '-x', name], name + '-before.txt')
capture(['cat', str(psy / 'uevent')], 'uevent-before.txt')
gadget = Path('/sys/kernel/config/usb_gadget/samurai/configs/c.1')
udc = Path('/sys/class/udc/a600000.usb')
usb = {name: (gadget / name).read_text().strip() for name in ['MaxPower', 'bmAttributes']}
usb.update({name: (udc / name).read_text().strip() for name in ['state', 'current_speed', 'maximum_speed']})
usb['typec_class_entries'] = len(list(Path('/sys/class/typec').glob('port*')))
(out / 'usb-descriptor-state.json').write_text(json.dumps(usb, indent=2) + '\n')
assert usb['state'] == 'configured'
capture(['cat', '/sys/class/power_supply/bq28z610-0/uevent'], 'gauge-before-private.txt')
# No forced address ownership. Temporarily release the already verified
# observation-only driver, then always rebind the same OF client in finally.
# No new_device/delete_device and no charger configuration writes occur.
released = False
start = time.monotonic()
try:
    driver.joinpath('unbind').write_text('0-005c\n')
    released = True
    assert client.exists() and not client.joinpath('driver').exists() and not psy.exists()
    capture([str(reader), '/dev/i2c-0'], 'registers-first.txt')
    capture([str(reader), '/dev/i2c-0'], 'registers-second.txt')
finally:
    if released:
        assert client.exists() and not client.joinpath('driver').exists()
        driver.joinpath('bind').write_text('0-005c\n')
assert client.joinpath('driver').resolve() == driver and psy.exists()
(out / 'binding-restoration.json').write_text(json.dumps(dict(same_of_client_rebound=True,
    unbound_seconds=round(time.monotonic() - start, 6), new_device_or_delete_device_used=False,
    forced_address_ownership=False, charger_configuration_data_writes=0), indent=2) + '\n')
capture(['cat', str(psy / 'uevent')], 'uevent-after.txt')
capture(['sha256sum', '-c', str(out / 'package-db-before.sha256')], 'package-db-final-check.txt')
for name, manifest in [('nv', '/run/samurai-wifi/nv-source-hashes.txt'),
                       ('source', '/var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256'),
                       ('vendor', '/var/lib/samurai/k115-vendor-camera-source/vendor-before.sha256')]:
    capture(['sha256sum', '-c', manifest], name + '-check.txt')
for name in ['phosh', 'phoc']:
    capture(['pgrep', '-x', name], name + '-after.txt')
capture(['cat', '/sys/class/power_supply/bq28z610-0/uevent'], 'gauge-after-private.txt')
capture(['dmesg'], 'dmesg-after-private.txt')
(out / 'final-taint.txt').write_text(Path('/proc/sys/kernel/tainted').read_text())
assert boot == Path('/proc/sys/kernel/random/boot_id').read_text()
(out / 'SHA256SUMS').write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ./' + p.name
    for p in sorted(out.iterdir()) if p.is_file()) + '\n')
subprocess.run(['tar', '-C', str(out), '-czf', '/tmp/k138-charge-contract-private.tar.gz', '.'], check=True, timeout=20)
print('K138_FIXED_READ_CONTRACT_SAME_PERMANENT_CLIENT_RESTORED_NO_CONFIG_WRITES', flush=True)
