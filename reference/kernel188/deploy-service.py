from pathlib import Path
import hashlib
import json
import host

ref = Path(__file__).resolve().parent
ssc = ref.parents[1] / 'linux-port/ssc'
files = [ssc / n for n in ['samurai-ssc.py', 'samurai-ssc.initd', 'iio-sensor-proxy.initd', 'iio-sensor-proxy.conf']]
files.append(ref / 'install-service.py')
host.ssh('test ! -e /var/lib/samurai/k188-tools && mkdir -m700 /var/lib/samurai/k188-tools')
for path in files:
    dest = '/var/lib/samurai/k188-tools/' + path.name
    host.upload(path, dest)
    host.ssh('sha256sum -c -', input=(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + dest + '\n').encode())
p = host.ssh('python3 /var/lib/samurai/k188-tools/install-service.py', timeout=55)
(host.PRIVATE / 'installation-private.log').write_bytes(p.stdout + p.stderr)
summary = json.loads(p.stdout)
(ref / 'service-installation-validation.json').write_text(json.dumps(summary, indent=2) + '\n')
p = host.ssh('tar -C /var/lib/samurai/k188-deploy -czf /tmp/k188-installation-private.tar.gz . && sha256sum /tmp/k188-installation-private.tar.gz')
digest = p.stdout.decode().split()[0]
archive = host.PRIVATE / 'installation-private.tar.gz'
host.download('/tmp/k188-installation-private.tar.gz', archive)
assert hashlib.sha256(archive.read_bytes()).hexdigest() == digest
print(json.dumps(summary))
