"""Locate the stock model-name branches without executing the OEM HAL."""
from pathlib import Path
import json,re,struct,subprocess
import host
P=host.PRIVATE;path=P/'hal-source/camera.qcom.so';raw=path.read_bytes()
offset=struct.unpack_from('<Q',raw,0x28)[0];stride,count,strings=struct.unpack_from('<HHH',raw,0x3a)
sections=[struct.unpack_from('<IIQQQQIIQQ',raw,offset+i*stride) for i in range(count)]
names=raw[sections[strings][4]:sections[strings][4]+sections[strings][5]]
sections={names[s[0]:].split(b'\0',1)[0].decode():s for s in sections}
text=sections['.text'];code=raw[text[4]:text[4]+text[5]]
frames=subprocess.check_output(['aarch64-linux-gnu-readelf','--debug-dump=frames',str(path)],text=True)
ranges=[tuple(int(x,16) for x in m) for m in re.findall(r'FDE .*?pc=([0-9a-f]+)\.\.([0-9a-f]+)',frames)]
records=[]
for needle in [b'fx319aa_imx319',b'imx319']:
 start=0;locations=[]
 while True:
  at=raw.find(needle+b'\0',start)
  if at<0:break
  start=at+1
  for section in sections.values():
   if section[4]<=at<section[4]+section[5]:locations.append(section[3]+at-section[4]);break
 for target in locations:
  refs=[]
  for pos in range(0,len(code)-28,4):
   word=struct.unpack_from('<I',code,pos)[0]
   if word&0x9f000000!=0x90000000:continue
   rd=word&31;imm=((word>>5&0x7ffff)<<2)|(word>>29&3)
   if imm&(1<<20):imm-=1<<21
   base=((text[3]+pos)&~4095)+(imm<<12)
   if base!=target&~4095:continue
   for nextpos in range(pos+4,pos+28,4):
    add=struct.unpack_from('<I',code,nextpos)[0]
    if add&0xff000000==0x91000000 and (add>>5&31)==rd:
     delta=(add>>10&4095)<<(12 if add&(1<<22) else 0)
     if base+delta==target:refs.append(text[3]+nextpos)
  functions=sorted(set((a,b) for pc in refs for a,b in ranges if a<=pc<b))
  for a,b in functions:
   disassembly=subprocess.check_output(['aarch64-linux-gnu-objdump','-d','--start-address='+hex(a),'--stop-address='+hex(b),str(path)],text=True)
   (P/('hal-eeprom-function-'+hex(a)+'.txt')).write_text(disassembly)
  records.append(dict(model=needle.decode(),string_virtual_address=hex(target),code_references=[hex(x) for x in refs],function_ranges=[[hex(a),hex(b)] for a,b in functions]))
(P/'hal-model-xrefs.json').write_text(json.dumps(records,indent=2)+'\n')
print(json.dumps({'fde_functions':len(ranges),'references':records},indent=2))
