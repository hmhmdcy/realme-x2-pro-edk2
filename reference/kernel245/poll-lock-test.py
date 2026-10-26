from pathlib import Path
import json
r=Path('/var/lib/samurai/k245-engine-lock');s=json.loads((r/'state-private.json').read_text());p=Path('/proc')/str(s['pid']);alive=p.exists() and p.joinpath('stat').read_text().split()[21]==str(s['start_ticks'])
report=dict(state=s,pid_live_and_matches=alive);private={}
if (r/'summary.json').exists():report['summary']=json.loads((r/'summary.json').read_text())
for name in ['failure-private.txt','restore-failure-private.txt']:
 if (r/name).exists():private[name]=(r/name).read_text()
report['completed_phases']=[json.loads(p.read_text()) for p in r.glob('*-summary.json')]
print(json.dumps({'report':report,'private':private}))
