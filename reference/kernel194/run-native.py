from pathlib import Path
import host,sys,subprocess
path=Path(sys.argv[1])
try:p=host.ssh('python3 -',input=path.read_bytes(),timeout=int(sys.argv[2]) if len(sys.argv)>2 else 120)
except subprocess.CalledProcessError as e:
 (host.PRIVATE/(path.stem+'-failed-private.log')).write_bytes((e.stdout or b'')+(e.stderr or b''));raise SystemExit('Native script failed; private log saved: '+path.stem)
(host.PRIVATE/(path.stem+'-host-private.log')).write_bytes(p.stdout+p.stderr);print(p.stdout.decode()[-5000:])
