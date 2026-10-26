from pathlib import Path
import json
r=Path('/var/lib/samurai');p=r/'k243-diag-query'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
records=[json.loads(x) for x in (p/'events-private.jsonl').read_text().splitlines()]
print(json.dumps(dict(report=json.loads((p/'summary.json').read_text()),private=dict(records=records,failure=(p/'failure-private.txt').read_text() if (p/'failure-private.txt').exists() else None,responses=json.loads((p/'responses-private.json').read_text())))))
