from pathlib import Path
import json
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k244-runtime/boot-id-private.txt').read_bytes();o=r/'k246-streaming-rf';state=json.loads((o/'state-private.json').read_text());p=Path('/proc',str(state['pid']));alive=p.exists() and p.joinpath('stat').read_text().split()[21]==state['start_ticks']
summary=json.loads((o/'summary.json').read_text()) if (o/'summary.json').exists() else None
print(json.dumps({'report':dict(stage=246,state=state,worker_alive=alive,summary=summary),'private':dict(failure=(o/'failure-private.txt').read_text() if (o/'failure-private.txt').exists() else None,cleanup_failure=(o/'cleanup-failure-private.txt').read_text() if (o/'cleanup-failure-private.txt').exists() else None)}))
