from pathlib import Path
import json,subprocess
import host

path=Path(__file__).resolve().parent/'probe-utc-injection.py'
try:p=host.ssh('python3 -',input=path.read_bytes(),timeout=65)
except subprocess.CalledProcessError as error:
 (host.PRIVATE/'utc-probe-failure-private.log').write_bytes(error.stdout+error.stderr);print(error.stderr.decode());raise
(host.PRIVATE/'utc-probe-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(path.parent/'utc-injection-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
