"""Check the actual submitted worker identity and compare its LUT words with source."""
from pathlib import Path
import json,re,subprocess
import host

ROOT=Path(__file__).resolve().parent
identity=json.loads((host.PRIVATE/'cst-constant-launch-private.json').read_text())
code=r'''
from pathlib import Path
import json
r=Path('/var/lib/samurai/k289-cst-r1');s=json.loads((r/'state-private.json').read_text());assert s['pid']==identity['pid']
p=Path('/proc',str(identity['pid']));live=False
if p.exists():
 fields=(p/'stat').read_text().rsplit(')',1)[1].split();live=fields[19]==identity['start_ticks'] and fields[0]!='Z'
print(json.dumps(dict(state=s,matching_worker_live=live,
 summary=json.loads((r/'summary-private.json').read_text()) if (r/'summary-private.json').exists() else None,
 failure=(r/'failure-private.txt').read_text() if (r/'failure-private.txt').exists() else None)))
'''
q=host.ssh('python3 -',input=('identity='+repr(identity)+'\n'+code).encode(),timeout=20)
data=json.loads(q.stdout);(host.PRIVATE/'cst-constant-poll-private.json').write_bytes(q.stdout)
print(json.dumps({k:v for k,v in data.items() if k!='summary'},indent=2))
if not data['summary']:raise SystemExit(0)
summary=data['summary'];(ROOT/'cst-constant-capture-validation.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
