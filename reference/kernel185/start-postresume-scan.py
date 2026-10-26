"""Separate scan after automatic Wi-Fi recovery; do not repeat the suspend."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import host

ref = Path(__file__).resolve().parent
value = (ref / 'test-bluez-scan-preserve-pairs.py').read_text()
value = value.replace('k185-baseline/boot-id-private.txt', 'k185-reboot-runtime/boot-id-private.txt')
path = ref / 'test-bluez-scan-postresume.py'
assert not path.exists()
path.write_text(value)
subprocess.run([sys.executable, '-m', 'py_compile', str(path)], check=True)
host.upload(path, '/var/lib/samurai/k185-tools/' + path.name)
host.upload(ref / 'analyze-scans.py', '/var/lib/samurai/k185-tools/analyze-scans.py')
host.ssh('sha256sum -c -', input=(hashlib.sha256(path.read_bytes()).hexdigest() +
         '  /var/lib/samurai/k185-tools/' + path.name + '\n').encode())
guard = '''from pathlib import Path
import json
root = Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes() == (root / 'k185-reboot-runtime/boot-id-private.txt').read_bytes()
pm = json.loads((root / 'k185-scan-after-suspend/powered-suspend/validation.json').read_text())
failure = json.loads((root / 'k185-scan-after-suspend/result.json').read_text())
state = json.loads((root / 'k185-postresume-inspection/summary.json').read_text())
assert pm['suspend_and_rtc_resume_passed'] and not failure['pass_all'] and not failure['rounds']
assert state['wifi_connected'] and state['wifi_frequency_mhz'] == 5180 and state['taint'] == 0
assert Path('/etc/bluetooth/main.conf').read_bytes().hex() != (root / 'k185post-policy/main.conf-before-private').read_bytes().hex()
assert not (root / 'k185-scan-postresume').exists()
'''
host.ssh('python3 -', input=guard.encode())
p = host.ssh('nohup python3 /var/lib/samurai/k185-tools/test-bluez-scan-postresume.py /var/lib/samurai/k185-scan-postresume > /var/lib/samurai/k185-scan-postresume-worker-private.log 2>&1 < /dev/null & echo $!')
(host.PRIVATE / 'postresume-scan-worker-pid-private.txt').write_bytes(p.stdout)
print(json.dumps({'delayed_postresume_scan_started': True, 'no_suspend_repeat': True,
    'wifi_recovered_automatically': True, 'three_discovery_modes': True}))
