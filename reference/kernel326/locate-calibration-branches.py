"""Locate the other model branches in the already pinned OEM EEPROM formatter."""
from pathlib import Path
import json,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
path=P.parent/'kernel316/hal-source/camera.qcom.so';raw=path.read_bytes();start,end=0x4fa058,0x50459c
names=['s5kgw1_p24c128e_sunny_19781','s5kgw1_p24c128e_sunny_19696','f3m5yae_s5k3m5sx','imx471_m24c64s'];records=[]
for name in names:
 locations=[];at=0
 while True:
  at=raw.find(name.encode()+b'\0',at)
  if at<0:break
  locations.append(at);at+=1
 refs=[]
 for target in locations:
  for pos in range(start,end-28,4):
   word=struct.unpack_from('<I',raw,pos)[0]
   if word&0x9f000000!=0x90000000:continue
   rd=word&31;imm=((word>>5&0x7ffff)<<2)|(word>>29&3)
   if imm&(1<<20):imm-=1<<21
   base=(pos&~4095)+(imm<<12)
   if base!=target&~4095:continue
   for off in range(pos+4,pos+28,4):
    add=struct.unpack_from('<I',raw,off)[0]
    if add&0xff000000==0x91000000 and (add>>5&31)==rd:
     delta=(add>>10&4095)<<(12 if add&(1<<22) else 0)
     if base+delta==target:refs.append(off)
  for ref in refs:
   text=subprocess.check_output(['aarch64-linux-gnu-objdump','-d','--start-address='+hex(ref-32),'--stop-address='+hex(min(end,ref+500)),str(path)],text=True)
   (P/(name+'-'+hex(ref)+'-branch.txt')).write_text(text)
 records.append(dict(eeprom_name=name,string_offsets=[hex(v) for v in locations],formatter_references=[hex(v) for v in sorted(set(refs))]))
(HERE/'stock-model-branches.json').write_text(json.dumps(dict(stage=326,source_stage=316,formatter_fde=[hex(start),hex(end)],models=records,phone_changed=False),indent=2)+'\n');print(json.dumps(records,indent=2))
