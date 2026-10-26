from pathlib import Path
import json
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k244-runtime/boot-id-private.txt').read_bytes();o=r/'k244-nextboot/capture';state=json.loads((o/'state-private.json').read_text());p=Path('/proc')/str(state['pid']);alive=p.exists() and p.joinpath('stat').read_text().split()[21]==str(state['start_ticks'])
private={n:(o/n).read_text() for n in ['diag-events-private.jsonl','loc-events-private.jsonl'] if (o/n).exists()}
if (o/'summary.json').exists():private['summary']=json.loads((o/'summary.json').read_text())
if (o/'failure-private.txt').exists():private['failure']=(o/'failure-private.txt').read_text()
print(json.dumps({'report':dict(stage=244,state=state,pid_alive_and_matches=alive,files=list(private)),'private':private}))
