from pathlib import Path
import host,subprocess,sys

path=Path(sys.argv[1])
try:p=host.ssh('python3 -',input=path.read_bytes(),timeout=int(sys.argv[2]) if len(sys.argv)>2 else 120)
except subprocess.CalledProcessError as error:
 (host.PRIVATE/(path.stem+'-failed-private.log')).write_bytes((error.stdout or b'')+(error.stderr or b''));raise SystemExit('Native operation failed; private evidence retained: '+path.stem)
(host.PRIVATE/(path.stem+'-host-private.log')).write_bytes(p.stdout+p.stderr)
print(p.stdout.decode()[-6000:])
