#!/usr/bin/env python3
"""Read-only completion after the source hash check timed out; never replay I2C."""
from pathlib import Path
import hashlib
import json
import os
import subprocess

out = Path('/var/lib/samurai/k133-charge-contract')
assert os.geteuid() == 0
assert os.uname().release == '7.3.0-rc6-rmx1931-samurai-k132+'
boot = (out / 'boot-id-private.txt').read_text()
assert boot == Path('/proc/sys/kernel/random/boot_id').read_text()
assert Path('/sys/bus/i2c/devices/0-005c/driver').resolve() == Path('/sys/bus/i2c/drivers/mp2650')
assert json.loads((out / 'binding-restoration.json').read_text())['same_of_client_rebound']
assert not (out / 'SHA256SUMS').exists()
assert not (out / 'source-check-timeout-r1.txt').exists()
(out / 'source-check.txt').rename(out / 'source-check-timeout-r1.txt')

def capture(args, name, timeout=60):
    assert not (out / name).exists()
    with (out / name).open('x') as log:
        subprocess.run(args, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=timeout)

capture(['sha256sum', '-c', '/var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256'], 'source-check-r2.txt')
capture(['sha256sum', '-c', '/var/lib/samurai/k115-vendor-camera-source/vendor-before.sha256'], 'vendor-check.txt')
capture(['sha256sum', '-c', str(out / 'package-db-before.sha256')], 'package-db-resume-check.txt')
for name in ['phosh', 'phoc']:
    capture(['pgrep', '-x', name], name + '-after.txt')
    assert (out / (name + '-before.txt')).read_text() == (out / (name + '-after.txt')).read_text()
capture(['cat', '/sys/class/power_supply/bq28z610-0/uevent'], 'gauge-after-private.txt')
capture(['dmesg'], 'dmesg-after-private.txt')
taint = Path('/proc/sys/kernel/tainted').read_text()
(out / 'final-taint.txt').write_text(taint)
assert taint.strip() == '0'
assert boot == Path('/proc/sys/kernel/random/boot_id').read_text()
(out / 'resume-validation.json').write_text(json.dumps(dict(original_failure='source hash check exceeded 10 seconds',
    resume_read_only=True, i2c_transactions_replayed=0, boot_unchanged=True, desktop_pids_unchanged=True,
    taint=0, source_vendor_package_hashes_passed=True), indent=2) + '\n')
(out / 'SHA256SUMS').write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ./' + p.name
    for p in sorted(out.iterdir()) if p.is_file()) + '\n')
assert not Path('/tmp/k133-charge-contract-private.tar.gz').exists()
subprocess.run(['tar', '-C', str(out), '-czf', '/tmp/k133-charge-contract-private.tar.gz', '.'], check=True, timeout=20)
print('K133_READONLY_RESUME_COMPLETE_NO_I2C_REPLAY', flush=True)
