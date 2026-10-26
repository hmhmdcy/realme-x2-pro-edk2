from pathlib import Path
import json
r=Path('/var/lib/samurai/k243-gnss-diag');state=json.loads((r/'state-private.json').read_text())
report={'state':state}
if (r/'summary.json').exists():report['summary']=json.loads((r/'summary.json').read_text())
private={}
if (r/'failure-private.txt').exists():private['failure']=(r/'failure-private.txt').read_text()
if (r/'diag-events-private.jsonl').exists():
 rows=[json.loads(x) for x in (r/'diag-events-private.jsonl').read_text().splitlines()]
 report['diag_records']=len(rows);report['diag_rx_records']=sum(x['kind']=='rx' for x in rows)
if (r/'events-private.jsonl').exists():report['loc_lines']=len((r/'events-private.jsonl').read_text().splitlines())
print(json.dumps({'report':report,'private':private}))
