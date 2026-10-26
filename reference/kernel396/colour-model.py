"""Execute target HAL CC calculation and CDM encoding; providers own storage only."""
from pathlib import Path
import importlib.util,struct
from unicorn.arm64_const import *
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('hal380',HERE.parent/'kernel380/hal-machine.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
DATA=h.DATA

class Colour(h.Machine):
 def step(self,u,pc,size,user):
  if pc in [0x4cd8b0,0x4cda68]:
   self.instructions+=1;self.providers[hex(pc)]=self.providers.get(hex(pc),0)+1
   if pc==0x4cd8b0:
    assert u.reg_read(UC_ARM64_REG_X0)==DATA+0xa000 and u.reg_read(UC_ARM64_REG_W1)==11
    result=DATA+0xb000
   else:
    assert u.reg_read(UC_ARM64_REG_X0)==DATA+0xa000;result=0
   u.reg_write(UC_ARM64_REG_X0,result);u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR));return
  return super().step(u,pc,size,user)
 def calculate(self,matrix,offsets,shift,fill=0):
  # Target OEM override path supplies an already interpolated CC region.
  input=DATA;override=DATA+0x1000;output=DATA+0x5000;regs=DATA+0x6000
  self.u.mem_write(input,bytes(256));self.u.mem_write(override,bytes(0x3000));self.u.mem_write(regs,bytes([fill])*64)
  self.u.mem_write(override+7524,struct.pack('<12f',*matrix,*offsets));self.u.mem_write(override+7580,struct.pack('<I',shift));self.u.mem_write(override+7576,struct.pack('<I',1))
  self.u.mem_write(output,struct.pack('<IIQ',1,0,regs));assert self.call(0x37f070,input,override,output,phase='original-cc13-calculate')==0
  assert bytes(self.u.mem_read(regs+36,28))==bytes([fill])*28
  return bytes(self.u.mem_read(regs,36))
 def command(self,registers):
  regs=DATA+0x6000;self.u.mem_write(regs,registers);self.u.mem_write(DATA+0xb000,bytes([0xa7])*64)
  assert self.call(0x52cb10,DATA+0xa000,0x5e68,9,regs,phase='original-cdm-register-range')==0
  assert bytes(self.u.mem_read(DATA+0xb000+44,20))==bytes([0xa7])*20
  return bytes(self.u.mem_read(DATA+0xb000,44))

def leaves(value):
 if isinstance(value,dict):
  if 'matrix' in value:yield value
  else:
   for child in value.values():yield from leaves(child)
 elif isinstance(value,list):
  for child in value:yield from leaves(child)
