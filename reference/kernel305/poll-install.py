from pathlib import Path
import json
import host
HERE=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json
root=Path('/var/lib/samurai/k305-geometry-r3')
state=json.loads((root/'transaction-state-private.json').read_text())
p=Path('/proc',str(state['pid']),'stat')
live=p.exists() and p.read_text().rsplit(')',1)[1].split()[0]!='Z' and p.read_text().rsplit(')',1)[1].split()[19]==state['start_ticks']
print(json.dumps(dict(state=state,worker_live=live,summary=json.loads((root/'summary-private.json').read_text()) if (root/'summary-private.json').exists() else None,
 failure=(root/'failure-private.txt').read_text() if (root/'failure-private.txt').exists() else None,
 restart_failure=(root/'restart-failure-private.txt').read_text() if (root/'restart-failure-private.txt').exists() else None)))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=20)
d=json.loads(q.stdout);(host.PRIVATE/'install-status-private.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps({k:d[k] for k in ['state','worker_live']},indent=2))
if d['summary'] is not None:
 (HERE/'geometry-install-r3-validation.json').write_text(json.dumps(d['summary'],indent=2)+'\n')
 (HERE/'geometry-install-validation.json').write_text(json.dumps(d['summary'],indent=2)+'\n')
 print(json.dumps(d['summary'],indent=2))
if d['failure'] or d['restart_failure']:
 print('FAILURE_DETAILS_RETAINED_PRIVATELY')
