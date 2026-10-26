from pathlib import Path
import json,time
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k201-baseline/boot-id-private.txt').read_bytes()
out=root/'k201-geoclue-auto';report=dict(summary_exists=(out/'summary.json').exists(),watch=json.loads((root/'gnss-assist/watch-state.json').read_text()))
if (out/'progress.json').exists():report['progress']=json.loads((out/'progress.json').read_text())
p=out/'locations-private.jsonl'
if p.exists():
 rows=p.read_text().splitlines();report['rows']=len(rows)
 if rows:report['last_elapsed']=json.loads(rows[-1])['elapsed'];report['last_write_age_seconds']=time.time()-p.stat().st_mtime
print(json.dumps(report))
