"""Apply the signed package-only transaction after its matched rollback was exported."""
from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((R/'rollback-validation.json').read_text())['phone_and_pc_copies_verified']
response=P/'package-install-response-private.log';assert not response.exists()
code=(R/'install-r23-worker.py').read_text();compile(code,'install-r23-worker.py','exec')
response.write_bytes(b'SUBMISSION INTENT: inspect k277-package-transaction state before repeating.\n')
q=host.ssh('python3 -',input=code.encode(),timeout=190,check=False);response.write_bytes(q.stdout+q.stderr)
assert q.returncode==0 and q.stdout,'Inspect existing transaction and actual process state before any recovery'
d=json.loads(q.stdout);(R/'package-install-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
assert d['packages_verified'] and d['camera_idle'] and not any(d['fault_delta'].values()) and d['taint']==0
