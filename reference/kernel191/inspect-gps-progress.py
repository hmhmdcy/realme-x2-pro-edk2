import host
code=b'''from pathlib import Path
import json,time
p=Path('/var/lib/samurai/k191-mm-stream/locations-private.jsonl');rows=p.read_text().splitlines();summary=p.parent/'summary.json'
print(json.dumps(dict(rows=len(rows),last_elapsed=json.loads(rows[-1])['elapsed'] if rows else None,last_write_age_seconds=time.time()-p.stat().st_mtime,summary_exists=summary.exists())))
'''
p=host.ssh('python3 -',input=code);print(p.stdout.decode())
