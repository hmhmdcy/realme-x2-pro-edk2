"""Original target HAL numerical paths and complete CDM packet encoder."""
from pathlib import Path
import importlib.util,struct
from unicorn.arm64_const import *
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('hal380',HERE.parent/'kernel380/hal-machine.py');h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
DATA=h.DATA
CV_FIELDS=['r_to_y','g_to_y','b_to_y','y_offset','ap','am','bp','bm','cp','cm','dp','dm','kcr','kcb']
class Colour(h.Machine):
 def step(self,u,pc,size,user):
  if pc in [0x4cd8b0,0x4cda68]:
   self.instructions+=1;self.providers[hex(pc)]=self.providers.get(hex(pc),0)+1
   assert u.reg_read(UC_ARM64_REG_X0)==DATA+0xa000
   if pc==0x4cd8b0:assert u.reg_read(UC_ARM64_REG_W1) in [10,11,14];result=DATA+0xb000
   else:result=0
   u.reg_write(UC_ARM64_REG_X0,result);u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR));return
  return super().step(u,pc,size,user)
 def cst(self,reserve):
  inp=DATA;override=inp+0x1000;out=inp+0x5000;regs=inp+0x6000
  self.u.mem_write(inp,bytes(256));self.u.mem_write(override,bytes(0x3000));self.u.mem_write(regs,bytes(64))
  self.u.mem_write(override+4160,struct.pack('<6I9f6i',*reserve['c_x0_tab'],*reserve['c_x1_tab'],*reserve['m_tab'],*reserve['o_tab'],*reserve['s_tab']))
  self.u.mem_write(out,struct.pack('<IIQ',2,0,regs));assert not self.call(0x37b4d8,inp,override,out,phase='original-ipe-cst')
  assert not any(bytes(self.u.mem_read(regs+48,16)));return bytes(self.u.mem_read(regs,48))
 def cc(self,matrix,offsets,shift):
  inp=DATA;override=inp+0x1000;out=inp+0x5000;regs=inp+0x6000
  self.u.mem_write(inp,bytes(256));self.u.mem_write(override,bytes(0x3000));self.u.mem_write(regs,bytes(64))
  self.u.mem_write(override+5676,struct.pack('<12f',*matrix,*offsets));self.u.mem_write(override+5732,struct.pack('<I',shift));self.u.mem_write(override+5728,struct.pack('<I',1))
  self.u.mem_write(out,struct.pack('<IIQ',2,0,regs));assert not self.call(0x37f070,inp,override,out,phase='original-ipe-cc')
  assert not any(bytes(self.u.mem_read(regs+36,28)));return bytes(self.u.mem_read(regs,36))
 def cv(self,data):
  obj=DATA+0xc000;inp=DATA+0xd000;override=DATA+0x1000
  for p,n in [(obj,1024),(inp,4096),(override,0x3000)]:self.u.mem_write(p,bytes(n))
  self.u.mem_write(inp+2792,struct.pack('<Q',override));self.u.mem_write(override+8864,struct.pack('<14f',*[data[k] for k in CV_FIELDS]));self.u.mem_write(override+8924,struct.pack('<I',1))
  self.u.reg_write(UC_ARM64_REG_X19,obj);self.u.reg_write(UC_ARM64_REG_X20,inp);self.u.reg_write(UC_ARM64_REG_SP,h.STACK+0xf0000)
  self.u.emu_start(0x34c374,0x34c59c,timeout=1000000,count=1000);assert self.u.reg_read(UC_ARM64_REG_PC)==0x34c59c
  assert not any(bytes(self.u.mem_read(obj+144,32)));return bytes(self.u.mem_read(obj+112,32))
 def command(self,address,registers):
  regs=DATA+0x6000;self.u.mem_write(regs,registers);self.u.mem_write(DATA+0xb000,bytes([0xa7])*80)
  assert not self.call(0x52cb10,DATA+0xa000,address,len(registers)//4,regs,phase='original-cdm')
  length=len(registers)+8;assert bytes(self.u.mem_read(DATA+0xb000+length,80-length))==bytes([0xa7])*(80-length)
  return bytes(self.u.mem_read(DATA+0xb000,length))
def leaves(nodes):
 for n in nodes:
  if 'children' in n:yield from leaves(n['children'])
  else:yield n
