"""Observe native producer writes and firmware consumers without enqueue."""
from pathlib import Path
import importlib.util,json,struct
from unicorn import UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE
from unicorn.arm64_const import UC_ARM64_REG_PC,UC_ARM64_REG_X0
from unicorn.arm_const import UC_ARM_REG_PC
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
module('storage284',HERE.parent/'kernel284/storage.py').mounted_build()
n=module('native425',HERE.parent/'kernel425/native-model.py');f=module('firmware425',HERE.parent/'kernel425/firmware-model.py')
def native(config,w,h,iq):
 class Trace(n.Native):
  def __init__(self):
   super().__init__();self.writes={};D=n.h.DATA
   def writing(u,access,address,size,value,user):
    lo=max(address,D+0x40000);hi=min(address+size,D+0x60000)
    for off in range(lo-(D+0x40000),hi-(D+0x40000)):self.writes[off]=u.reg_read(UC_ARM64_REG_PC)
   self.u.hook_add(UC_HOOK_MEM_WRITE,writing)
 m=Trace();raw,bl,capacity=m.striping(config,w,h,2,iq)
 return raw,m.writes,bl
def firmware(config,raw,iq,w,h):
 old=f.r.Firmware;reads={}
 class Trace(old):
  def __init__(self):
   super().__init__();base=f.f.DATA+0x30000
   def reading(u,access,address,size,value,user):
    for off in range(max(address,base)-base,min(address+size,base+len(raw))-base):reads.setdefault(off,set()).add(u.reg_read(UC_ARM_REG_PC))
   self.u.hook_add(UC_HOOK_MEM_READ,reading,begin=base,end=base+len(raw)-1)
 f.r.Firmware=Trace
 try:result=f.prepare(config,raw,iq,w,h,46080)
 finally:f.r.Firmware=old
 return result,reads
if __name__=='__main__':
 for w,h in [(640,480),(650,480)]:
  config=(P.parent/f'kernel425/width-{w}-dc-1-config-private.bin').read_bytes();iq=(P.parent/f'kernel424/coarse-width-{w}-dc-1-iq-private.bin').read_bytes()
  raw,writes,bl=native(config,w,h,iq);(model,job,commands,meta),reads=firmware(config,raw,iq,w,h)
  (P/f'{w}-writes-private.json').write_text(json.dumps(writes)+'\n');(P/f'{w}-reads-private.json').write_text(json.dumps({str(k):sorted(v) for k,v in reads.items()})+'\n')
  (P/f'{w}-native-stripe-private.bin').write_bytes(raw)
  rows=[]
  for a,z,name in [(0,24,'global'),(24,436,'coarse-pass'),(436,848,'full-pass'),(2268,2892,'coarse-stripe'),(2892,len(raw),'full-stripes')]:
   fields=[]
   for off in range(a,z,2):
    if any(i in reads for i in [off,off+1]):fields.append(dict(offset=off-a,value=struct.unpack_from('<H',raw,off)[0],writer=hex(writes[off]) if off in writes else None))
   rows.append(dict(name=name,fields=fields))
  (P/f'{w}-consumed-fields-private.json').write_text(json.dumps(rows,indent=2)+'\n')
  print(json.dumps(dict(width=w,height=h,striping_bytes=len(raw),produced_bytes=len(writes),consumed_bytes=len(reads),bl=bl)),flush=True)
