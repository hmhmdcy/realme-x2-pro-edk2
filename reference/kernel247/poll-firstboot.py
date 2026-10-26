from pathlib import Path
import json
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k247-runtime/boot-id-private.txt').read_bytes();o=r/'k247-nextboot/capture';s=json.loads((o/'state-private.json').read_text());p=Path('/proc',str(s['pid']));alive=p.exists() and p.joinpath('stat').read_text().split()[21]==s['start_ticks']
summary=json.loads((o/'summary.json').read_text()) if (o/'summary.json').exists() else None
print(json.dumps({'report':dict(stage=247,state=s,worker_alive_and_identity_matches=alive,summary=summary),'private':dict(failure=(o/'failure-private.txt').read_text() if (o/'failure-private.txt').exists() else None,cleanup_failure=(o/'cleanup-failure-private.txt').read_text() if (o/'cleanup-failure-private.txt').exists() else None)}))
