from pathlib import Path
import hashlib
import host

ref = Path(__file__).resolve().parent
host.ssh('test -f /var/lib/samurai/k186-reboot-runtime/summary.json && test ! -e /var/lib/samurai/k186-load-fastrpc')
for path in [host.PRIVATE / 'fastrpc-k186-private.ko', ref / 'fastrpc-module-build-validation.json',
             ref / 'load-fastrpc-candidate.py', ref / 'kmsg-collector.py']:
    dest = '/var/lib/samurai/k186-tools/' + path.name
    host.upload(path, dest)
    host.ssh('sha256sum -c -', input=(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + dest + '\n').encode())
p = host.ssh('python3 /var/lib/samurai/k186-tools/load-fastrpc-candidate.py', timeout=45)
(host.PRIVATE / 'candidate-load-host-private.log').write_bytes(p.stdout + p.stderr)
print(p.stdout.decode().strip())
