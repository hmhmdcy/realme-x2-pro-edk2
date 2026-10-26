"""Run one reviewed native preflight or install, retaining its exact response."""
from pathlib import Path
import json
import sys
import host

R=Path(__file__).resolve().parent;step=sys.argv[1];assert step in ['preflight','install']
if step=='install':assert json.loads((R/'native-preflight-validation.json').read_text())['native_phone_solver_passed']
q=host.ssh('python3 -',input=(R/('native-'+step+'.py')).read_bytes(),timeout=110,check=False)
(host.PRIVATE/(step+'-response-private.log')).write_bytes(q.stdout+q.stderr)
assert q.returncode==0 and q.stdout,'Read the native transaction context before any retry'
report=json.loads(q.stdout)
(R/('native-'+step+'-validation.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
