from pathlib import Path
import hashlib
import json
import subprocess
import host

ref = Path(__file__).resolve().parent
for name in ['test-persistent-client.py', 'verify-persistent-runtime.py']:
    path = ref / name
    dest = '/var/lib/samurai/k188-tools/' + name
    host.upload(path, dest)
    host.ssh('sha256sum -c -', input=(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + dest + '\n').encode())
# Only this non-private, code-only client is readable by the desktop user.
host.ssh('mkdir -p /usr/share/samurai/ssc && cp /var/lib/samurai/k188-tools/test-persistent-client.py /usr/share/samurai/ssc/test-persistent-client.py && chmod 644 /usr/share/samurai/ssc/test-persistent-client.py')
script = (ref / 'verify-persistent-runtime.py').read_text().replace('/var/lib/samurai/k188-tools/test-persistent-client.py', '/usr/share/samurai/ssc/test-persistent-client.py')
try:
    p = host.ssh('python3 -', input=script.encode(), timeout=100)
except subprocess.CalledProcessError as error:
    (host.PRIVATE / 'persistent-client-failure-private.log').write_bytes(error.stdout + error.stderr)
    raise
(host.PRIVATE / 'persistent-client-host-private.log').write_bytes(p.stdout + p.stderr)
report = json.loads(p.stdout)
(ref / 'persistent-client-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
