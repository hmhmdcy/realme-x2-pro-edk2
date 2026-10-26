from pathlib import Path
import json
r=Path('/var/lib/samurai');report={};private={}
for name in ['k243-wlan-control','k243-wlan-off-clock']:
 p=r/name
 if not p.exists():continue
 report[name]=dict(state=json.loads((p/'state-private.json').read_text()))
 if (p/'summary.json').exists():report[name]['summary']=json.loads((p/'summary.json').read_text())
 if (p/'failure-private.txt').exists():private[name]=(p/'failure-private.txt').read_text()
 if (p/'events-private.jsonl').exists():report[name]['loc_lines']=len((p/'events-private.jsonl').read_text().splitlines())
print(json.dumps({'report':report,'private':private}))
