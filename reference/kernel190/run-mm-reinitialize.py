from pathlib import Path
import json,subprocess
import host

ref=Path(__file__).resolve().parent
try:p=host.ssh('python3 -',input=(ref/'reinitialize-mm-debug.py').read_bytes(),timeout=125)
except subprocess.CalledProcessError as error:
 (host.PRIVATE/'mm-reinit-failure-private.log').write_bytes(error.stdout+error.stderr);print(error.stderr.decode());raise
(host.PRIVATE/'mm-reinit-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(ref/'mm-reinitialize-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
