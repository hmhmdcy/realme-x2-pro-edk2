"""Instruction oracle for RGB Bayer regions and the original16x16 pooling."""
from pathlib import Path
import struct,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'kernel336'))
from stock_lux import StockLux
from stock_emulator import OBJECT,STACK,STOP
from unicorn.arm64_const import *
PROC=OBJECT+0x1000;PARENT=PROC-0x80;STATS=OBJECT+0x80000;RAW=OBJECT+0x82000
DESCRIPTOR=PROC+0x5d0f8;LEGACY=PROC+0x150a0
class StockBayer(StockLux):
 def __init__(self,path):
  super().__init__(path)
  self.allowed += [(0x4e5d0,0x4ed60),(0x3d608,0x3d650),(0x3d68c,0x3d744),(0x3cedc,0x3cff4),(0x3d7b8,0x3d818)]
 def region_setup(self,pixels,bits,high,weights,normalization=1.):
  self.write(PROC+32,'<QQ4f',pixels,pixels,1./(1<<(bits-8)),*weights)
  self.write(PROC+120,'<I',1)
  self.write(DESCRIPTOR,'<Q',STATS);self.write(DESCRIPTOR+20,'<I',4);self.write(DESCRIPTOR+28,'<II',0,0);self.write(DESCRIPTOR+36,'<f',normalization)
  self.write(STATS+72,'<I4II',0,*high,3072);self.write(STATS+104,'<Q',RAW)
  self.uc.mem_write(PROC+160,bytes(3072*4))
 def region(self,sums,counts,index=0):
  self.write(RAW+index*24,'<4I4H',*sums,*counts);self.begin=0x4e5d0
  self.write(PROC+160+index*4,'<I',0);self.call(x0=PROC,x1=index)
  assert self.uc.reg_read(UC_ARM64_REG_W0)==0
  return self.read(PROC+0x30a8+index*24,'<2f')
 def pool(self,columns,rows):
  assert columns%16==rows%16==0 and columns*rows<=3072
  sp=STACK+0xd000;self.uc.mem_write(sp+320,bytes(256));self.uc.mem_write(LEGACY,bytes(2048))
  self.write(PARENT+256,'<II',columns,rows)
  for index in range(columns*rows):
   for r,v in [(UC_ARM64_REG_SP,sp),(UC_ARM64_REG_X26,PARENT),(UC_ARM64_REG_W27,index),(UC_ARM64_REG_W21,24),(UC_ARM64_REG_W20,columns//16),(UC_ARM64_REG_W25,rows//16),(UC_ARM64_REG_X19,sp+320),(UC_ARM64_REG_X24,0x15120)]:self.uc.reg_write(r,v)
   self.uc.emu_start(0x3d608,0x3d650,timeout=2000000,count=100)
   assert self.uc.reg_read(UC_ARM64_REG_PC)==0x3d650
  self.write(sp+160,'<QQQ',PROC,0,STATS)
  self.uc.reg_write(UC_ARM64_REG_X26,PARENT);self.uc.reg_write(UC_ARM64_REG_SP,sp)
  self.uc.emu_start(0x3d68c,0x3d744,timeout=2000000,count=10000)
  assert self.uc.reg_read(UC_ARM64_REG_PC)==0x3d744
  self.calls+=1;return [self.read(LEGACY+i*8,'<2f') for i in range(256)]
 def weights(self,tuning,reference,current,enabled=True,input_valid=True):
  settings=OBJECT+0xf0000;pointer=OBJECT+0xef000
  self.write(PARENT+128,'<Q',pointer);self.write(pointer,'<Q',settings)
  self.write(settings+56,'<3fI3f',*tuning,int(enabled),*reference)
  self.write(PARENT+136,'<I3f',int(input_valid),*current)
  self.uc.reg_write(UC_ARM64_REG_SP,STACK+0xd000);self.uc.reg_write(UC_ARM64_REG_X26,PARENT);self.uc.reg_write(UC_ARM64_REG_X12,pointer)
  self.uc.reg_write(UC_ARM64_REG_X23,0x5bc88)
  self.uc.emu_start(0x3cedc,0x3cff4,timeout=2000000,count=1000)
  assert self.uc.reg_read(UC_ARM64_REG_PC)==0x3cff4
  self.calls+=1;return self.read(PARENT+180,'<3f')
