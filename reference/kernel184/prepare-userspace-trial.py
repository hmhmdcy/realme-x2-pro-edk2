from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import host

parser = argparse.ArgumentParser()
parser.add_argument('--start', action='store_true')
args = parser.parse_args()
ref = Path(__file__).resolve().parent
text = (ref / 'test-sensor-light.sh').read_text().replace('light-v1', 'light-v3')
text = text.replace('k184-baseline-r2/boot-id-private.txt', 'k184-reboot-runtime/boot-id-private.txt')
text = text.replace('timeout -s TERM -k 3 110 ', 'timeout -s TERM -k 3 140 ')
text = text.replace('timeout -s TERM -k 2 55 python3 -B /var/lib/samurai/k184-tools/ssc-light-probe.py --output "$dest/light" --duration 20',
                    'timeout -s TERM -k 2 85 python3 -B /var/lib/samurai/k184-tools/test-libssc-userspace.py --output "$dest/userspace"')
script = ref / 'test-sensor-userspace.sh'
script.write_text(text)
subprocess.run(['sh', '-n', str(script)], check=True)
if not args.start:
    print(json.dumps({'prepared': True, 'phone_changed': False}))
    raise SystemExit(0)
host.ssh('test -f /var/lib/samurai/k184-libssc-r2/build-validation.json && test ! -e /var/lib/samurai/k184-sensor-light-v3')
for p in [script, ref / 'test-libssc-userspace.py']:
    host.upload(p, '/var/lib/samurai/k184-tools/' + p.name)
    digest = hashlib.sha256(p.read_bytes()).hexdigest()
    host.ssh('sha256sum -c -', input=(digest + '  /var/lib/samurai/k184-tools/' + p.name + '\n').encode())
result = host.ssh('nohup sh /var/lib/samurai/k184-tools/test-sensor-userspace.sh > /var/lib/samurai/k184-userspace-v3-worker-private.log 2>&1 < /dev/null & echo $!')
(host.PRIVATE / 'userspace-v3-worker-pid-private.txt').write_bytes(result.stdout)
print(json.dumps({'trial_started': True, 'system_library_replaced': False}))
