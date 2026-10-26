"""Locate the original HAL write governing data-collection geometry."""
from pathlib import Path
import json,struct,sys
import oracle as o
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.arm64_const import UC_ARM64_REG_PC,UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_LR,UC_ARM64_REG_X25,UC_ARM64_REG_X22,UC_ARM64_REG_X21,UC_ARM64_REG_X20
import host
Base=o.r.h.Machine
records=[]
class Traced(Base):
 def __init__(self):
  super().__init__();self.u.hook_add(UC_HOOK_MEM_WRITE,self.write,begin=o.r.h.DATA+0x20000+408,end=o.r.h.DATA+0x20000+420)
  self.u.hook_add(UC_HOOK_MEM_WRITE,self.write,begin=0x60035e8,end=0x60035fc)
  self.u.hook_add(UC_HOOK_MEM_WRITE,self.write,begin=0x6002e88,end=0x6002ea0)
  self.u.hook_add(UC_HOOK_MEM_WRITE,self.write,begin=0x20eeb6c,end=0x20eeb7c)
  self.u.hook_add(UC_HOOK_MEM_WRITE,self.write,begin=0x20ef1d0,end=0x20ef1e0)
  self.u.hook_add(UC_HOOK_MEM_WRITE,self.write,begin=0x20ef238,end=0x20ef240)
  self.u.hook_add(UC_HOOK_MEM_WRITE,self.write,begin=0x20ef818,end=0x20ef820)
 def write(self,u,access,address,size,value,user):records.append(dict(pc=hex(u.reg_read(UC_ARM64_REG_PC)),address=hex(address),size=size,value=value))
 def step(self,u,pc,size,user):
  if pc==0x146474:records.append(dict(source=hex(u.reg_read(UC_ARM64_REG_X25)+400)))
  if pc==0x152924:records.append(dict(input_source=hex(u.reg_read(UC_ARM64_REG_X22)+82)))
  if pc==0x159e20:records.append(dict(root_source=hex(u.reg_read(UC_ARM64_REG_X21)+104)))
  if pc==0x152164:records.append(dict(config_source=hex(u.reg_read(UC_ARM64_REG_X20)+668)))
  if pc==0x5b1290:
   a,b,c=[u.reg_read(r) for r in [UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2]]
   for target in [o.r.h.DATA+0x20000+416,0x6002e94]:
    if a<=target<a+c:records.append(dict(copy_caller=hex(u.reg_read(UC_ARM64_REG_LR)),source=hex(b+target-a),target=hex(target),value=struct.unpack('<I',u.mem_read(b+target-a,4))[0]))
  return super().step(u,pc,size,user)
o.r.h.Machine=Traced
w,h=map(int,sys.argv[1:3]) if len(sys.argv)>1 else (640,480)
blob,_,_=o.striping(w,h,8,1,o.iq_blob(1,1))
(host.PRIVATE/f'dc-write-trace-{w}x{h}-private.json').write_text(json.dumps(records,indent=2)+'\n')
print(json.dumps(dict(width=w,height=h,flag=struct.unpack_from('<H',blob,416)[0],records=records)))
