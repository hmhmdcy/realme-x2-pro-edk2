"""Run complete target IFE GTM Execute; record only transport boundaries."""
from pathlib import Path
import importlib.util,struct
from unicorn.arm64_const import *
s=importlib.util.spec_from_file_location('gtm432transport',Path(__file__).resolve().parents[1]/'kernel432/gtm-model.py');n=importlib.util.module_from_spec(s);s.loader.exec_module(n);h=n.h
class Machine(n.Machine):
 def __init__(self):
  super().__init__();self.dmi=[];self.fail_dmi=False;self.calculations=0
 def step(self,u,pc,size,user):
  if pc==0x37c818:self.calculations+=1
  if pc==0x52d2e8:
   args=[u.reg_read(UC_ARM64_REG_X0+i) for i in range(6)];assert args[1]==0xc24 and args[2] in [24,25] and args[3]==self.dmi_command and args[5]==512
   self.dmi.append(dict(config=args[1],selector=args[2],offset=args[4],bytes=args[5],payload=bytes(u.mem_read(self.dmi_buffer+args[4],512)),failed=self.fail_dmi))
   u.reg_write(UC_ARM64_REG_X0,int(self.fail_dmi));u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR));return
  super().step(u,pc,size,user)
 def create(self,chromatix,offset_words=14):
  D=h.DATA;self.inp=D+0x30000;self.tags=D+0x40000;self.calculated=D+0x50000;self.dmi_buffer=D+0x60000;self.dmi_command=D+0x70000;self.adrc=D+0x80000
  create=D+0x20000;self.u.mem_write(create,bytes(128));assert self.call(0x31f7f0,create,phase='complete-native-gtm-create')==0;self.obj=self.read64(create);assert self.obj
  self.u.mem_write(self.obj+248,struct.pack('<Q',chromatix));self.u.mem_write(self.obj+36,struct.pack('<I',offset_words))
  return self.obj
 def execute(self,adrc,force=True,lux=140.0,locks=(0,0)):
  u=self.u;D=h.DATA;inp=self.inp;u.mem_write(inp,bytes(20032));u.mem_write(self.tags,bytes(128));u.mem_write(self.tags+98,bytes(locks));u.mem_write(self.adrc,adrc)
  for at,value in [(0,D+0x71000),(16,D+0x71100),(80,D+0x71200),(104,self.dmi_command),(112,self.dmi_buffer),(2512,self.tags),(2528,self.calculated),(2760,D+0x75000),(2768,D+0x71300),(3024,self.adrc)]:u.mem_write(inp+at,struct.pack('<Q',value))
  u.mem_write(inp+3016,struct.pack('<I',1));u.mem_write(inp+19896,struct.pack('<I',force))
  for at,value in [(2872,2.),(2880,4.),(2884,2.),(2892,lux),(2912,2.),(2916,1.2)]:u.mem_write(inp+at,struct.pack('<f',value))
  u.mem_write(self.calculated+964,struct.pack('<I',0xa6a6a6a0));u.mem_write(self.dmi_buffer,bytes([0xa7])*4096)
  before=len(self.writes);dmi_before=len(self.dmi);calc_before=self.calculations
  result=self.call(0x31fc00,self.obj,inp,phase='complete-native-ife-gtm-execute')
  return dict(result=result,register_writes=self.writes[before:],dmi=self.dmi[dmi_before:],calculated_enable=self.read32(self.calculated+964),calculations=self.calculations-calc_before,next_selector=self.u.mem_read(self.obj+236,1)[0],next_bank=self.read32(self.obj+232)&1)
