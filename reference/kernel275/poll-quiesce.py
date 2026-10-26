"""Poll the same submitted worker; never restart it after a timeout."""
from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json
root=Path('/var/lib/samurai/k275-quiesce');state=json.loads((root/'state-private.json').read_text())
proc=Path('/proc',str(state['pid']));live=proc.exists()
result=dict(state=state,worker_present=live,summary=json.loads((root/'summary.json').read_text()) if (root/'summary.json').exists() else None,
 failure=(root/'failure-private.txt').read_text() if (root/'failure-private.txt').exists() else None)
print(json.dumps(result))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=20)
(host.PRIVATE/'quiesce-poll-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
print(json.dumps(dict(state=d['state'],worker_present=d['worker_present'],summary=d['summary'],failure=d['failure']),indent=2))
if d['summary']:(R/'quiesce-validation.json').write_text(json.dumps(d['summary'],indent=2)+'\n')
