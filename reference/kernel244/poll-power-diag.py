from pathlib import Path
import json
p=Path('/var/lib/samurai/k244-power-diag');report=dict(state=json.loads((p/'state-private.json').read_text()));private={}
if (p/'summary.json').exists():report['summary']=json.loads((p/'summary.json').read_text())
if (p/'failure-private.txt').exists():private['failure']=(p/'failure-private.txt').read_text()
if (p/'diag-events-private.jsonl').exists():
 rows=[json.loads(x) for x in (p/'diag-events-private.jsonl').read_text().splitlines()];report['events']=[{k:v for k,v in x.items() if k not in ['hex','node','port']} for x in rows];private['diag_records']=rows
print(json.dumps({'report':report,'private':private}))
