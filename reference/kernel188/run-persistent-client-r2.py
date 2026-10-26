from pathlib import Path
import hashlib
import json
import subprocess
import host

ref = Path(__file__).resolve().parent
for name in ['run-client-in-active-session.py', 'test-active-desktop-client.py']:
    path = ref / name
    dest = '/var/lib/samurai/k188-tools/' + name if name.startswith('run-') else '/usr/share/samurai/ssc/' + name
    host.upload(path, dest)
    host.ssh('sha256sum -c -', input=(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + dest + '\n').encode())
    if name.startswith('test-'):
        host.ssh('chmod 644 ' + dest)
script = (ref / 'verify-persistent-runtime.py').read_text()
script = script.replace('k188-persistent-client', 'k188-persistent-client-r2')
script = script.replace("['su', '-s', '/bin/sh', 'cy122', '-c', 'python3 /var/lib/samurai/k188-tools/test-persistent-client.py']",
    "['python3', '/var/lib/samurai/k188-tools/run-client-in-active-session.py']")
try:
    p = host.ssh('python3 -', input=script.encode(), timeout=100)
except subprocess.CalledProcessError as error:
    (host.PRIVATE / 'persistent-client-r2-failure-private.log').write_bytes(error.stdout + error.stderr)
    raise
(host.PRIVATE / 'persistent-client-r2-host-private.log').write_bytes(p.stdout + p.stderr)
report = json.loads(p.stdout)
(ref / 'persistent-client-r2-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
