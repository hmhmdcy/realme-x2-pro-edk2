from pathlib import Path
import json,re
import host
P=host.PRIVATE;raw=(P/'hal-source/camera.qcom.so').read_bytes();result={}
for p in sorted(P.glob('hal-helper-*.txt')):
 lines=p.read_text().splitlines();found=[]
 for i,line in enumerate(lines):
  m=re.search(r'adrp\s+(x\d+), ([0-9a-f]+)',line)
  if not m:continue
  reg=m[1];base=int(m[2],16)
  for nxt in lines[i+1:i+7]:
   add=re.search(r'add\s+x\d+, '+reg+r', #0x([0-9a-f]+)',nxt)
   if not add:continue
   address=base+int(add[1],16)
   if address>=0xd7000:continue
   value=raw[address:].split(b'\0',1)[0]
   if 3<len(value)<350 and all(c in [9,10,13] or 32<=c<127 for c in value):found.append((hex(address),value.decode()))
 result[p.stem]=list(dict.fromkeys(found))
(P/'hal-helper-string-context.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
