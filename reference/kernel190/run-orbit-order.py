from pathlib import Path
import json,subprocess
import host

ref=Path(__file__).resolve().parent
try:p=host.ssh('python3 -',input=(ref/'probe-orbit-order.py').read_bytes(),timeout=65)
except subprocess.CalledProcessError as error:
 (host.PRIVATE/'orbit-order-failure-private.log').write_bytes(error.stdout+error.stderr);print(error.stderr.decode());raise
(host.PRIVATE/'orbit-order-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(ref/'orbit-order-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
