"""Run one saved native script through the existing authenticated transport."""
from pathlib import Path
import host,sys,subprocess
p=Path(sys.argv[1])
try:result=host.ssh('python3 -',input=p.read_bytes(),timeout=int(sys.argv[2]) if len(sys.argv)>2 else 900)
except subprocess.CalledProcessError as error:
 (host.PRIVATE/(p.stem+'-host-private.log')).write_bytes(error.stdout+error.stderr)
 print('Native script failed; private log saved:',p.stem);raise SystemExit(error.returncode)
(host.PRIVATE/(p.stem+'-host-private.log')).write_bytes(result.stdout+result.stderr)
print(result.stdout.decode()[-3000:]);print('exit',result.returncode)
raise SystemExit(result.returncode)
