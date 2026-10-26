from pathlib import Path
import json
result=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  args=(p/'cmdline').read_bytes()
  if b'prepare-rootfs-owner-fix.py' not in args and b'cp\0-a\0-T\0' not in args:continue
  if b'inspect-preparation-process' in args:continue
  fields=(p/'stat').read_text().split();status=(p/'status').read_text().splitlines()
  result.append(dict(pid=int(p.name),state=fields[2],wait=(p/'wchan').read_text().strip(),rss=next((l for l in status if l.startswith('VmRSS:')),''),cpu_ticks=int(fields[13])+int(fields[14])))
 except (FileNotFoundError,ProcessLookupError):pass
print(json.dumps(result),flush=True)
