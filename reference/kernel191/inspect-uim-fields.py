import host
code=b'''from pathlib import Path
import json,re
out=Path('/var/lib/samurai/k191-uim-status');records={}
for p in out.glob('*-private.txt'):
 safe=[]
 for line in p.read_text().splitlines():
  if re.match(r"^\\s*(?:Card state|Slot state|Card status|Slot status)\\s*:",line,re.I):safe.append(line.strip())
 records[p.name]=safe
print(json.dumps(records))
'''
p=host.ssh('python3 -',input=code);print(p.stdout.decode())
