from pathlib import Path
import subprocess
import host

ref = Path(__file__).resolve().parent
for name in ['load-fastrpc-default-r2.py','fastrpc-host-tests-validation.json']:
    host.upload(ref / name, '/var/lib/samurai/k186-tools/' + name)
try:
    p = host.ssh('python3 /var/lib/samurai/k186-tools/load-fastrpc-default-r2.py',timeout=45)
except subprocess.CalledProcessError as e:
    (host.PRIVATE / 'default-load-r2-failed-private.log').write_bytes(e.stdout+e.stderr)
    print(e.stderr.decode(errors='replace'))
    raise SystemExit(e.returncode)
(host.PRIVATE / 'default-load-r2-host-private.log').write_bytes(p.stdout+p.stderr)
print(p.stdout.decode().strip())
