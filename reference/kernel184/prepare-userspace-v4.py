from pathlib import Path
import hashlib
import json
import subprocess
import host

ref = Path(__file__).resolve().parent
text = (ref / 'test-sensor-userspace.sh').read_text().replace('light-v3', 'light-v4')
text = text.replace('k184-reboot-runtime/boot-id-private.txt', 'k184-reboot-runtime-r2/boot-id-private.txt')
path = ref / 'test-sensor-userspace-v4.sh'
path.write_text(text)
subprocess.run(['sh', '-n', str(path)], check=True)
host.ssh('test ! -e /var/lib/samurai/k184-sensor-light-v4 && test -f /var/lib/samurai/k184-reboot-runtime-r2/boot-id-private.txt')
for p in [path, ref / 'test-libssc-userspace.py']:
    host.upload(p, '/var/lib/samurai/k184-tools/' + p.name)
    digest = hashlib.sha256(p.read_bytes()).hexdigest()
    host.ssh('sha256sum -c -', input=(digest + '  /var/lib/samurai/k184-tools/' + p.name + '\n').encode())
result = host.ssh('nohup sh /var/lib/samurai/k184-tools/test-sensor-userspace-v4.sh > /var/lib/samurai/k184-userspace-v4-worker-private.log 2>&1 < /dev/null & echo $!')
(host.PRIVATE / 'userspace-v4-worker-pid-private.txt').write_bytes(result.stdout)
print(json.dumps({'corrected_sensor_proxy_trial_started': True, 'system_library_replaced': False}))
