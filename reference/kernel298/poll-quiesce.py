"""Observe the submitted quiesce worker, without resubmitting it."""
from pathlib import Path
import json
import host

ROOT=Path(__file__).resolve().parent
identity=json.loads((host.PRIVATE/'quiesce-launch-private.json').read_text())
code=r'''
from pathlib import Path
import json
r=Path('/var/lib/samurai/k298-quiesce')
state=json.loads((r/'state-private.json').read_text());assert state['pid']==identity['pid']
p=Path('/proc',str(identity['pid']));live=False
if p.exists():
 fields=(p/'stat').read_text().rsplit(')',1)[1].split()
 live=fields[19]==identity['start_ticks'] and fields[0]!='Z'
report=dict(state=state,matching_worker_live=live,
            summary=json.loads((r/'summary.json').read_text()) if (r/'summary.json').exists() else None,
            failure=(r/'failure-private.txt').read_text() if (r/'failure-private.txt').exists() else None)
print(json.dumps(report))
'''
q=host.ssh('python3 -',input=('identity='+repr(identity)+'\n'+code).encode(),timeout=20)
report=json.loads(q.stdout);(host.PRIVATE/'quiesce-poll-private.json').write_bytes(q.stdout)
if report['summary']:
 assert report['state']['terminal'] and report['state']['exit_code']==0
 (ROOT/'quiesce-validation.json').write_text(json.dumps(report['summary'],indent=2)+'\n')
print(json.dumps(report,indent=2))
