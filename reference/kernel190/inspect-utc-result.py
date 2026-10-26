from pathlib import Path
import json
import host

code='''from pathlib import Path
import json,gi
gi.require_version('Qmi','1.0')
from gi.repository import Qmi
report=json.loads(Path('/var/lib/samurai/k190-utc-injection/summary.json').read_text())
report.update(probe_process_exit=1,cleanup_api_error='Qmi.Device uses close_async, not close')
print(json.dumps(report));print(Qmi.Device.close_async.__doc__)
'''
p=host.ssh('python3 -',input=code.encode());(host.PRIVATE/'utc-result-inspection-private.log').write_bytes(p.stdout)
record=json.loads(p.stdout.decode().splitlines()[0]);(Path(__file__).resolve().parent/'utc-first-probe-validation.json').write_text(json.dumps(record,indent=2)+'\n')
print(p.stdout.decode())
