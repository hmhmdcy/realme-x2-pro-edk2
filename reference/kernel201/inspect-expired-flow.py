from pathlib import Path
import json
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k201-baseline/boot-id-private.txt').read_bytes()
r=json.loads((root/'k201-real-expired-flow/summary.json').read_text());r['watch']=json.loads((root/'gnss-assist/watch-state.json').read_text())
p=root/'k201-geoclue-expired-auto/progress.json'
if p.exists():r['progress']=json.loads(p.read_text())
print(json.dumps(r))
