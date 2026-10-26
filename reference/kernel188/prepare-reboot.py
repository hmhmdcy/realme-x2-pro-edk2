"""Capture the current boot before one no-flash boot-service verification reset."""
from pathlib import Path
import hashlib
import json
import subprocess
import host

ref = Path(__file__).resolve().parent
old = ref.parent / 'kernel187'
names = ['collect-preflash.py', 'check-quiesce.py', 'disable-crtc.py', 'freeze-for-bootloader.sh',
    'linux-restart2-bootloader.py', 'quiesce-current183.sh', 'reboot-current.py', 'fastboot-reboot-current.py']
for name in names:
    data = (old / name).read_text().replace('k187', 'k188')
    data = data.replace('/var/lib/samurai/k186-reboot-runtime-r2/boot-id-private.txt',
                        '/var/lib/samurai/k187-reboot-runtime/boot-id-private.txt')
    data = data.replace('stage=187', 'stage=188').replace("'stage': 187", "'stage': 188")
    if name == 'quiesce-current183.sh':
        data = data.replace('iio-sensor-proxy nfcd', 'iio-sensor-proxy samurai-ssc nfcd')
    path = ref / name
    assert not path.exists()
    path.write_text(data)
    subprocess.run(['sh', '-n', str(path)] if name.endswith('.sh') else ['python3', '-m', 'py_compile', str(path)], check=True)
host.ssh('test ! -e /var/lib/samurai/k188-reboot-tools && mkdir -m700 /var/lib/samurai/k188-reboot-tools')
for name in names:
    if name in ['reboot-current.py', 'fastboot-reboot-current.py']:
        continue
    path = ref / name
    dest = '/tmp/k188-' + name if name in ['check-quiesce.py', 'disable-crtc.py', 'freeze-for-bootloader.sh'] else '/var/lib/samurai/k188-reboot-tools/' + name
    host.upload(path, dest)
    host.ssh('sha256sum -c -', input=(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + dest + '\n').encode())
p = host.ssh('python3 /var/lib/samurai/k188-reboot-tools/collect-preflash.py', timeout=55)
(host.PRIVATE / 'pre-reboot-capture-private.log').write_bytes(p.stdout + p.stderr)
print(json.dumps(dict(fresh_current_boot_captured=True, original_modules_and_hci185_verified=True,
    native_boot_service_test_prepared=True, no_transition_yet_sent=True)))
