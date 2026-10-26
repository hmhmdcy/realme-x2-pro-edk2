from pathlib import Path
import json
import re
import subprocess
import time
import host

marker = host.PRIVATE / 'fastboot-reboot-private.json'
assert not marker.exists()
assert (host.PRIVATE / 'reboot-request-private.json').exists()
fb = '/mnt/c/Users/cy122/Downloads/platform-tools/platform-tools/fastboot.exe'


def command(args, name):
    result = subprocess.run([fb, *args], capture_output=True, timeout=15, check=True)
    (host.PRIVATE / (name + '-private.log')).write_bytes(result.stdout + result.stderr)
    return (result.stdout + result.stderr).decode()


deadline = time.monotonic() + 30
attempt = 0
while True:
    attempt += 1
    devices = command(['devices'], 'current-fastboot-devices-' + str(attempt))
    observed = re.findall(r'(?m)^(\S+)\s+fastboot\s*$', devices)
    if observed or time.monotonic() >= deadline:
        break
    time.sleep(1)
assert len(observed) == 1
expected = json.loads((host.PRIVATE.parent / 'kernel109/fastboot-identity.json').read_text())['serial']
assert observed[0] == expected
serial = observed[0]
product = command(['-s', serial, 'getvar', 'product'], 'current-fastboot-product')
assert re.search(r'product:\s*msmnile\b', product)
marker.write_text(json.dumps({'actual_serial': serial, 'request_count': 1, 'flash_requested': False}, indent=2) + '\n')
command(['-s', serial, 'reboot'], 'current-fastboot-reboot')
print(json.dumps({'fresh_fastboot_identity_verified': True, 'single_reboot_requested': True,
                  'partitions_flashed': []}))
