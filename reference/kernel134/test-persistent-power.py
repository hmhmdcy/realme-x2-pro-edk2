#!/usr/bin/env python3
from pathlib import Path
import hashlib
import json
import os
import stat
import subprocess
import time

out = Path('/var/lib/samurai/k134-persistent-power')
first = Path('/var/lib/samurai/k134-first-runtime')
psy = Path('/sys/class/power_supply/mp2650-input')
client = Path('/sys/bus/i2c/devices/0-005c')
driver = Path('/sys/bus/i2c/drivers/mp2650')
usb = Path('/sys/class/power_supply/samurai-usb-input')
assert usb.joinpath('device/of_node').resolve() == Path('/sys/firmware/devicetree/base/soc@0/spmi@c440000/pmic@2/usb-input@1300')
boot = Path('/proc/sys/kernel/random/boot_id').read_text()
assert boot == (first / 'boot-id-private.txt').read_text()
assert os.uname().release == '7.3.0-rc6-rmx1931-samurai-k134+'
assert client.joinpath('driver').resolve() == driver and psy.is_dir()
assert client.joinpath('of_node').resolve() == Path('/sys/firmware/devicetree/base/soc@0/geniqup@8c0000/i2c@884000/charger@5c')
assert not out.exists()
out.mkdir(mode=0o700)
(out / 'boot-id-private.txt').write_text(boot)
def capture(args, name, timeout=60, check=True):
    with (out / name).open('w') as log:
        return subprocess.run(args, stdout=log, stderr=subprocess.STDOUT, check=check, timeout=timeout).returncode
capture(['dmesg'], 'dmesg-before-private.txt')
capture(['sha256sum', '/etc/apk/world', '/lib/apk/db/installed'], 'package-db-before.sha256')
capture(['pgrep', '-x', 'phosh'], 'phosh-before.txt')
capture(['pgrep', '-x', 'phoc'], 'phoc-before.txt')
capture(['iw', 'dev', 'wlan0', 'link'], 'wifi-link-private.txt')
capture(['rc-service', 'bluetooth', 'status'], 'bluez-service.txt')
permissions = {p: stat.S_IMODE((psy / p).stat().st_mode) for p in ['online', 'status', 'voltage_now', 'current_now']}
assert all(m == 0o444 for m in permissions.values())
usb_permissions = {p: stat.S_IMODE((usb / p).stat().st_mode) for p in ['online', 'usb_type', 'current_max']}
assert all(m == 0o444 for m in usb_permissions.values())
(out / 'usb-permissions.json').write_text(json.dumps(usb_permissions, indent=2) + '\n')
(out / 'permissions.json').write_text(json.dumps(permissions, indent=2) + '\n')
samples = []
started = time.monotonic()
for index in range(8):
    assert boot == Path('/proc/sys/kernel/random/boot_id').read_text()
    assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
    assert client.joinpath('driver').resolve() == driver
    item = dict(sample=index, elapsed_seconds=round(time.monotonic() - started, 3), properties={})
    for prop in ['online', 'status', 'voltage_now', 'current_now', 'uevent']:
        try:
            item['properties'][prop] = {'value': (psy / prop).read_text()}
        except OSError as error:
            item['properties'][prop] = {'errno': error.errno}
    assert item['properties']['online']['value'].strip() == '1'
    assert item['properties']['status']['value'].strip() in ['Full', 'Charging', 'Not charging']
    assert 'POWER_SUPPLY_ONLINE=1\n' in item['properties']['uevent']['value']
    item['usb_input'] = {p: (usb / p).read_text() for p in ['online', 'usb_type', 'current_max', 'uevent']}
    assert item['usb_input']['online'].strip() == '1'
    assert int(item['usb_input']['current_max']) in [1500000, 3000000]
    samples.append(item)
    (out / 'samples-private.json').write_text(json.dumps(samples, indent=2) + '\n')
    if index != 7:
        time.sleep(6)
capture(['pgrep', '-x', 'phosh'], 'phosh-after.txt')
capture(['pgrep', '-x', 'phoc'], 'phoc-after.txt')
capture(['dmesg'], 'dmesg-after-private.txt')
capture(['sha256sum', '-c', str(out / 'package-db-before.sha256')], 'package-db-final-check.txt')
capture(['sha256sum', '-c', '/run/samurai-wifi/nv-source-hashes.txt'], 'nv-check.txt')
capture(['sha256sum', '-c', '/var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256'], 'source-check.txt')
capture(['sha256sum', '-c', '/var/lib/samurai/k115-vendor-camera-source/vendor-before.sha256'], 'vendor-check.txt')
(out / 'final-taint.txt').write_text(Path('/proc/sys/kernel/tainted').read_text())
manifest = '\n'.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ./' + p.name for p in sorted(out.iterdir()) if p.is_file()) + '\n'
(out / 'SHA256SUMS').write_text(manifest)
subprocess.run(['tar', '-C', str(out), '-czf', '/tmp/k134-persistent-power-private.tar.gz', '.'], check=True, timeout=20)
print('K134_PERSISTENT_DT_BOUND_READONLY_STANDARD_POWER_8_SAMPLE_CAPTURE_COMPLETE', flush=True)
