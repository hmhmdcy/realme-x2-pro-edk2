from pathlib import Path
import json
import subprocess
import host

ref=Path(__file__).resolve().parent
try:
    p=host.ssh('python3 -',input=(ref/'rollback-auto-service.py').read_bytes(),timeout=120)
except subprocess.CalledProcessError as error:
    (host.PRIVATE/'rollback-failure-private.log').write_bytes(error.stdout+error.stderr)
    raise
(host.PRIVATE/'rollback-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout)
(ref/'rollback-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
