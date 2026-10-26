"""Find stock LSC-formatting code from its string references and unwind ranges."""
from pathlib import Path
import json,re,struct,subprocess
HERE=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel320');P.mkdir(mode=0o700,exist_ok=True)
path=P.parent/'kernel316/hal-source/camera.qcom.so';raw=path.read_bytes()
off=struct.unpack_from('<Q',raw,0x28)[0];stride,count,strings=struct.unpack_from('<HHH',raw,0x3a)
sections=[struct.unpack_from('<IIQQQQIIQQ',raw,off+i*stride) for i in range(count)]
names=raw[sections[strings][4]:sections[strings][4]+sections[strings][5]]
sections={names[s[0]:].split(b'\0',1)[0].decode():s for s in sections}
text=sections['.text'];code=raw[text[4]:text[4]+text[5]]
frames=subprocess.check_output(['aarch64-linux-gnu-readelf','--debug-dump=frames',str(path)],text=True)
ranges=[tuple(int(x,16) for x in m) for m in re.findall(r'FDE .*?pc=([0-9a-f]+)\.\.([0-9a-f]+)',frames)]
targets={}
for needle in [b'FormatLSCData',b'FormatDataTypeByte',b'meshHWRollOffSize out of bound',b'Memory allocation for LSC failed']:
 start=0
 while True:
  at=raw.find(needle+b'\0',start)
  if at<0:break
  start=at+1
  for section in sections.values():
   if section[4]<=at<section[4]+section[5]:targets[section[3]+at-section[4]]=needle.decode();break
refs={v:[] for v in targets}
pages={v&~4095 for v in targets}
for pos in range(0,len(code)-32,4):
 word=struct.unpack_from('<I',code,pos)[0]
 if word&0x9f000000!=0x90000000:continue
 rd=word&31;imm=((word>>5&0x7ffff)<<2)|(word>>29&3)
 if imm&(1<<20):imm-=1<<21
 base=((text[3]+pos)&~4095)+(imm<<12)
 if base not in pages:continue
 for n in range(pos+4,pos+32,4):
  add=struct.unpack_from('<I',code,n)[0]
  if add&0xff000000!=0x91000000 or (add>>5&31)!=rd:continue
  target=base+((add>>10&4095)<<(12 if add&(1<<22) else 0))
  if target in refs:refs[target].append(text[3]+n)
records=[]
for target,pcs in refs.items():
 functions=sorted(set((a,b) for pc in pcs for a,b in ranges if a<=pc<b))
 for a,b in functions:
  textout=subprocess.check_output(['aarch64-linux-gnu-objdump','-d','--start-address='+hex(a),'--stop-address='+hex(b),str(path)],text=True)
  (P/('stock-lsc-'+hex(a)+'.txt')).write_text(textout)
 records.append(dict(string=targets[target],string_va=hex(target),refs=[hex(pc) for pc in pcs],functions=[[hex(a),hex(b)] for a,b in functions]))
(P/'stock-lsc-xrefs.json').write_text(json.dumps(records,indent=2)+'\n');print(json.dumps(records,indent=2))
