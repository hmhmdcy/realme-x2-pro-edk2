from pathlib import Path
import json,os
p=Path('/var/lib/samurai/k246-quiesce');s=json.loads((p/'state-private.json').read_text());report=dict(state=s,pid_present=Path('/proc',str(s['pid'])).exists());private={}
if (p/'summary.json').exists():report['summary']=json.loads((p/'summary.json').read_text())
if (p/'failure-private.txt').exists():private['failure']=(p/'failure-private.txt').read_text()
print(json.dumps({'report':report,'private':private}))
