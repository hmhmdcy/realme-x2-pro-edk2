from pathlib import Path
import host,json,subprocess

here=Path(__file__).resolve().parent
prior=host.PRIVATE/'package-file-differences-private.json'
if prior.exists():
 backup=host.PRIVATE/'package-file-differences-drvfs-private.json';assert not backup.exists();backup.write_bytes(prior.read_bytes())
host.upload(host.PRIVATE/'upstream-payload-manifest.json','/var/lib/samurai/k203-package-records/upstream-payload-manifest.json')
try:p=host.ssh('python3 -',input=(here/'audit-current-package-files.py').read_bytes(),timeout=70)
except subprocess.CalledProcessError as error:
 (host.PRIVATE/'package-file-audit-failed-private.log').write_bytes((error.stdout or b'')+(error.stderr or b''));raise SystemExit('Package asset audit failed; private evidence retained')
(host.PRIVATE/'package-file-audit-private.log').write_bytes(p.stdout+p.stderr)
host.download('/var/lib/samurai/k203-package-file-audit-r2/differences-private.json',host.PRIVATE/'package-file-differences-private.json')
print(p.stdout.decode())
