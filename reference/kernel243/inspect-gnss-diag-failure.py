from pathlib import Path
import json
r=Path('/var/lib/samurai/k243-gnss-diag')
rows=[json.loads(x) for x in (r/'diag-events-private.jsonl').read_text().splitlines()]
report={'state':json.loads((r/'state-private.json').read_text()),'events':[{k:v for k,v in x.items() if k not in ['hex','node','port']} for x in rows]}
print(json.dumps({'report':report,'private':{'events':rows,'failure':(r/'failure-private.txt').read_text()}}))
