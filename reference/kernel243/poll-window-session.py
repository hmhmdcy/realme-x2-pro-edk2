from pathlib import Path
import json
r=Path('/var/lib/samurai/k243-window-clock');s=json.loads((r/'state-private.json').read_text());report={'state':s}
if (r/'summary.json').exists():report['summary']=json.loads((r/'summary.json').read_text())
if (r/'events-private.jsonl').exists():report['loc_lines']=len((r/'events-private.jsonl').read_text().splitlines())
print(json.dumps({'report':report,'private':{'failure':(r/'failure-private.txt').read_text() if (r/'failure-private.txt').exists() else None}}))
