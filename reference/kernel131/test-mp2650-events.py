#!/usr/bin/env python3
"""Bounded temporary binding of the existing observation-only MP2650 driver."""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import time

out = Path('/var/lib/samurai/k131-mp2650-events-r2')
bus = Path('/sys/bus/i2c/devices/i2c-0')
client = Path('/sys/bus/i2c/devices/0-005c')
driver = Path('/sys/bus/i2c/drivers/mp2650')
boot = Path('/proc/sys/kernel/random/boot_id').read_text()
assert boot == Path('/var/lib/samurai/k130-warmboot-r2/boot-id-private.txt').read_text()
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
assert bus.joinpath('of_node').resolve() == Path('/sys/firmware/devicetree/base/soc@0/geniqup@8c0000/i2c@884000')
assert driver.is_dir() and not client.exists()
assert not out.exists()
tools = {'/var/lib/samurai/k131-read-mp2650': '6ef5467f5a445d718bd783ed86aabe5e93d08c442f483978355ad42ec79d5673',
         '/var/lib/samurai/k131-read-mp2650-input': 'ed25b9f497ec10294976f61b4fb67994f3884a42a1d7bc3778e0045f7a9ef3a7'}
for name, expected in tools.items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == expected
    Path(name).chmod(0o700)
out.mkdir(mode=0o700)
(out / 'boot-id-private.txt').write_text(boot)

def capture(args, name, check=True):
    with (out / name).open('w') as log:
        return subprocess.run(args, stdout=log, stderr=subprocess.STDOUT, check=check, timeout=8).returncode

capture(['sha256sum', '/etc/apk/world', '/lib/apk/db/installed'], 'package-db-before.sha256')
capture(['dmesg'], 'dmesg-before.txt')
capture([next(iter(tools)), '/dev/i2c-0'], 'registers-before.txt')
capture(['cat', '/sys/class/power_supply/bq28z610-0/uevent'], 'battery-before-private.txt')
created = False
samples = []
try:
    bus.joinpath('new_device').write_text('mp2650 0x5c\n')
    created = True
    assert client.joinpath('driver').resolve() == driver
    psy = Path('/sys/class/power_supply/mp2650-input')
    assert psy.exists()
    permissions = {prop: stat.S_IMODE((psy / prop).stat().st_mode) for prop in ['online', 'status', 'voltage_now', 'current_now']}
    assert all(mode & 0o222 == 0 for mode in permissions.values())
    refusal = capture(['/var/lib/samurai/k131-read-mp2650-input', '/dev/i2c-0'], 'busy-reader-refusal.txt', check=False)
    assert refusal != 0
    for index in range(8):
        item = {'sample': index, 'uptime': float(Path('/proc/uptime').read_text().split()[0]), 'properties': {}}
        for prop in ['online', 'status', 'voltage_now', 'current_now', 'uevent']:
            try:
                item['properties'][prop] = {'value': (psy / prop).read_text()}
            except OSError as error:
                item['properties'][prop] = {'errno': error.errno}
        samples.append(item)
        (out / 'samples-private.json').write_text(json.dumps(samples, indent=2) + '\n')
        if index != 7:
            time.sleep(1)
    (out / 'permissions.json').write_text(json.dumps(permissions, indent=2) + '\n')
finally:
    if created and client.exists():
        assert client.joinpath('driver').resolve() == driver
        bus.joinpath('delete_device').write_text('0x5c\n')
assert not client.exists()
capture([next(iter(tools)), '/dev/i2c-0'], 'registers-after.txt')
capture(['dmesg'], 'dmesg-after.txt')
capture(['cat', '/sys/class/power_supply/bq28z610-0/uevent'], 'battery-after-private.txt')
capture(['sha256sum', '-c', str(out / 'package-db-before.sha256')], 'package-db-final-check.txt')
(out / 'final-taint.txt').write_text(Path('/proc/sys/kernel/tainted').read_text())
(out / 'client-final-absent.txt').write_text('true\n')
capture(['pgrep', '-x', 'phosh'], 'phosh-final.txt')
capture(['pgrep', '-x', 'phoc'], 'phoc-final.txt')
manifest = '\n'.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ./' + p.name for p in sorted(out.iterdir()) if p.is_file()) + '\n'
(out / 'SHA256SUMS').write_text(manifest)
archive = Path('/tmp/k131-mp2650-events-r2-private.tar.gz')
subprocess.run(['tar', '-C', str(out), '-czf', str(archive), '.'], check=True)
Path(str(archive) + '.sha256').write_text(hashlib.sha256(archive.read_bytes()).hexdigest() + '  ' + str(archive) + '\n')
print('MP2650_EIGHT_SAMPLES_CAPTURED_OBSERVATION_CLIENT_REMOVED')
