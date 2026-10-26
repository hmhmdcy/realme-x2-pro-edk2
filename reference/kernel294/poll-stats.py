"""Observe the same physical capture worker and preserve failures."""
from pathlib import Path
import json
import host
ROOT=Path(__file__).resolve().parent
identity=json.loads((host.PRIVATE/'stats-launch-private.json').read_text())
code=r'''
from pathlib import Path
import json
root=Path('/var/lib/samurai/k294-stats-r1');state=json.loads((root/'state-private.json').read_text());assert state['pid']==identity['pid']
p=Path('/proc',str(identity['pid']));live=False
if p.exists():
 f=(p/'stat').read_text().rsplit(')',1)[1].split();live=f[19]==identity['start_ticks'] and f[0]!='Z'
print(json.dumps(dict(state=state,matching_worker_live=live,
 summary=json.loads((root/'summary-private.json').read_text()) if (root/'summary-private.json').exists() else None,
 failure=(root/'failure-private.txt').read_text() if (root/'failure-private.txt').exists() else None)))
'''
q=host.ssh('python3 -',input=('identity='+repr(identity)+'\n'+code).encode(),timeout=20)
report=json.loads(q.stdout);(host.PRIVATE/'stats-poll-private.json').write_bytes(q.stdout)
if report['summary']:(ROOT/'stats-capture-validation.json').write_text(json.dumps(report['summary'],indent=2)+'\n')
print(json.dumps(report,indent=2))
