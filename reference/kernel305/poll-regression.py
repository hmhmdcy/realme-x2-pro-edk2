from pathlib import Path
import json
import host
HERE=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json
root=Path('/var/lib/samurai/k305-four-camera-regression-r1');s=json.loads((root/'state-private.json').read_text())
p=Path('/proc',str(s['pid']),'stat')
live=p.exists() and p.read_text().rsplit(')',1)[1].split()[0]!='Z' and p.read_text().rsplit(')',1)[1].split()[19]==s['start_ticks']
print(json.dumps(dict(state={k:v for k,v in s.items() if k!='runs'},worker_live=live,
 legs=[{k:r[k] for k in ['leg','camera','frames','exit','passed']} for r in s['runs']],
 summary=json.loads((root/'summary.json').read_text()) if (root/'summary.json').exists() else None,
 failure=(root/'failure-private.txt').read_text() if (root/'failure-private.txt').exists() else None)))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=20)
d=json.loads(q.stdout);(host.PRIVATE/'regression-status-private.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps({k:d[k] for k in ['state','worker_live','legs']},indent=2))
if d['summary'] is not None:
 (HERE/'four-camera-regression-validation.json').write_text(json.dumps(d['summary'],indent=2)+'\n')
 print(json.dumps({k:v for k,v in d['summary'].items() if k!='legs'},indent=2))
if d['failure']:print('FAILURE_RETAINED_PRIVATELY')
