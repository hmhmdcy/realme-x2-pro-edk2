"""Inspect the one submitted physical-camera worker."""
from pathlib import Path
import json
import host

ROOT=Path(__file__).resolve().parent
identity=json.loads((host.PRIVATE/'four-camera292-launch-private.json').read_text())
code=r'''
from pathlib import Path
import json
r=Path('/var/lib/samurai/k292-four-camera-regression-r1');state=json.loads((r/'state-private.json').read_text());assert state['pid']==identity['pid']
p=Path('/proc',str(identity['pid']));live=False
if p.exists():
 f=(p/'stat').read_text().rsplit(')',1)[1].split();live=f[19]==identity['start_ticks'] and f[0]!='Z'
print(json.dumps(dict(state={k:v for k,v in state.items() if k!='runs'},legs=state['runs'],matching_worker_live=live,
 summary=json.loads((r/'summary.json').read_text()) if (r/'summary.json').exists() else None,
 failure=(r/'failure-private.txt').read_text() if (r/'failure-private.txt').exists() else None)))
'''
q=host.ssh('python3 -',input=('identity='+repr(identity)+'\n'+code).encode(),timeout=20)
report=json.loads(q.stdout);(host.PRIVATE/'four-camera292-poll-private.json').write_bytes(q.stdout)
if report['summary']:(ROOT/'four-camera-regression-validation.json').write_text(json.dumps(report['summary'],indent=2)+'\n')
print(json.dumps(dict(state=report['state'],matching_worker_live=report['matching_worker_live'],
 legs=[{k:r[k] for k in ['leg','camera','frames','exit','passed']} for r in report['legs']],
 passed=None if not report['summary'] else report['summary']['passed'],failure=report['failure']),indent=2))
