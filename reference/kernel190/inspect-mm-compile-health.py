import host
code=b'''from pathlib import Path
import json
jobs=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  name=(p/'comm').read_text().strip()
  if name in ['lto1','cc1','ld','ld.bfd','ninja','gcc','collect2','lto-wrapper']:
   text=(p/'status').read_text();jobs.append(dict(name=name,state=next(x for x in text.splitlines() if x.startswith('State:')),rss=next((x for x in text.splitlines() if x.startswith('VmRSS:')),None)))
 except FileNotFoundError:pass
thermal={p.name:(p/'temp').read_text().strip() for p in Path('/sys/class/thermal').glob('thermal_zone*') if (p/'temp').exists()}
mem=[x for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith(('MemAvailable:','SwapFree:'))]
print(json.dumps(dict(jobs=jobs,memory=mem,maximum_thermal_c=max(int(v) for v in thermal.values())/1000)))
'''
p=host.ssh('python3 -',input=code);print(p.stdout.decode())
