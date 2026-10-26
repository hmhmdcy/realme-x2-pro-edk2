"""Run a fresh policy-bounded suspend and discovery trial on the new boot."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import host

ref = Path(__file__).resolve().parent
policy = (ref / 'setup-scan-policy.py').read_text()
policy = policy.replace('k185-policy', 'k185post-policy')
policy = policy.replace('k185-baseline/boot-id-private.txt', 'k185-reboot-runtime/boot-id-private.txt')
policy = policy.replace('main.conf.k185-new', 'main.conf.k185post-new')
path = ref / 'setup-postboot-scan-policy.py'
assert not path.exists()
path.write_text(policy)
source = (ref / 'test-bluez-scan-preserve-pairs.py').read_text()
source = source.replace('k185-baseline/boot-id-private.txt', 'k185-reboot-runtime/boot-id-private.txt')
marker = "save('adapter-powered-private.json',p); sample()"
addition = """
    pm = subprocess.run(['python3', '/var/lib/samurai/k185-tools/test-powered-suspend.py',
                         str(root / 'powered-suspend')], capture_output=True, timeout=90)
    (root / 'suspend-run-private.log').write_bytes(pm.stdout + pm.stderr)
    assert pm.returncode == 0, 'RTC Bluetooth suspend trial failed; preserve its records'
    sample()"""
assert source.count(marker) == 1
source = source.replace(marker, marker + addition)
scan = ref / 'test-bluez-scan-after-suspend.py'
assert not scan.exists()
scan.write_text(source)
for path in [path, scan, ref / 'test-powered-suspend.py']:
    subprocess.run([sys.executable, '-m', 'py_compile', str(path)], check=True)
    host.upload(path, '/var/lib/samurai/k185-tools/' + path.name)
    host.ssh('sha256sum -c -', input=(hashlib.sha256(path.read_bytes()).hexdigest() +
             '  /var/lib/samurai/k185-tools/' + path.name + '\n').encode())
host.ssh('test -f /var/lib/samurai/k185-reboot-runtime/summary.json && test ! -e /var/lib/samurai/k185-scan-after-suspend')
p = host.ssh('python3 /var/lib/samurai/k185-tools/setup-postboot-scan-policy.py', timeout=40)
(host.PRIVATE / 'postboot-policy-private.log').write_bytes(p.stdout + p.stderr)
p = host.ssh('nohup python3 /var/lib/samurai/k185-tools/test-bluez-scan-after-suspend.py /var/lib/samurai/k185-scan-after-suspend > /var/lib/samurai/k185-scan-after-suspend-worker-private.log 2>&1 < /dev/null & echo $!')
(host.PRIVATE / 'after-suspend-worker-pid-private.txt').write_bytes(p.stdout)
print(json.dumps({'new_boot_trial_started': True, 'rtc_s2idle_seconds': 45,
    'bluetooth_powered_idle_then_three_discovery_modes': True, 'no_pairing_or_connection_requested': True}))
