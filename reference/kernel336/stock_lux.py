"""Restricted instruction oracle for the retained AEC exposure/lux paths."""
from pathlib import Path
import math,struct,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'kernel329'))
from stock_emulator import StockMath,OBJECT,OUT,LOGGER,STACK,STOP
from unicorn.arm64_const import *
INPUT=OBJECT+0x10000;INDEX=OBJECT+0x11000;LAYER=OBJECT+0x12000;TUNING=OBJECT+0x13000;TABLE=OBJECT+0x14000;CELLS=OBJECT+0x15000;MANAGER=OBJECT+0x16000;VTABLE=OBJECT+0x17000
GET_CELLS=LOGGER+0x200
class StockLux(StockMath):
 def __init__(self,path):
  self.allowed=[(0x2dbd8,0x2dce8),(0x272b8,0x27300),(0x4aee0,0x4b220)]
  self.log_calls=0;self.cells_calls=0;self.visited=set()
  super().__init__(path,0x4b088,0x4b220)
  self.write(0x5bcb0,'<Q',LOGGER)
  self.write(INPUT,'<Q',INDEX);self.write(INPUT+16,'<Q',LAYER);self.write(LAYER,'<Q',TUNING);self.write(INPUT+56,'<Q',TABLE)
  self.write(OBJECT+8,'<Q',MANAGER);self.write(MANAGER+112,'<Q',VTABLE);self.write(VTABLE+64,'<Q',GET_CELLS)
 def _step(self,uc,pc,size,_):
  self.instructions+=1;self.visited.add(pc)
  if pc in [0x58740,0x586f0,LOGGER,GET_CELLS]:
   if pc==0x58740:
    value=struct.unpack('<d',struct.pack('<Q',uc.reg_read(UC_ARM64_REG_D0)))[0];assert value>0 and math.isfinite(value),('log10',value,self.calls)
    uc.reg_write(UC_ARM64_REG_D0,struct.unpack('<Q',struct.pack('<d',math.log10(value)))[0]);self.log_calls+=1
   elif pc==GET_CELLS:uc.reg_write(UC_ARM64_REG_X0,CELLS);self.cells_calls+=1
   else:uc.reg_write(UC_ARM64_REG_X0,0);self.stub_calls+=1
   uc.reg_write(UC_ARM64_REG_PC,uc.reg_read(UC_ARM64_REG_LR));return
  if not any(a<=pc<b for a,b in self.allowed):raise RuntimeError('Unexpected AEC path '+hex(pc))
  if struct.unpack('<I',uc.mem_read(pc,4))[0]&0xffe0001f==0xd4000001:raise RuntimeError('SVC rejected')
 def manual(self,anchor,gain,nanoseconds):
  self.write(OBJECT,'<f',anchor[0]);self.write(OBJECT+8,'<Q',anchor[1]);self.write(OBJECT+20,'<f',anchor[2])
  self.write(OUT,'<f',gain);self.write(OUT+8,'<Q',nanoseconds);self.begin=0x2dbd8;self.call();return self.read(OUT+16,'<f')[0]
 def sensitivity(self,anchor,correction,sensitivity):
  self.write(TABLE,'<f',correction);self.write(TABLE+16,'<Q',LAYER)
  self.write(LAYER,'<f',anchor[0]);self.write(LAYER+8,'<Q',anchor[1]);self.write(LAYER+20,'<f',anchor[2]);self.write(OUT,'<f',sensitivity)
  self.uc.reg_write(UC_ARM64_REG_SP,STACK+0xf000);self.uc.reg_write(UC_ARM64_REG_LR,STOP)
  for r,v in [(UC_ARM64_REG_X0,TABLE),(UC_ARM64_REG_X20,OUT),(UC_ARM64_REG_X19,OUT+32)]:self.uc.reg_write(r,v)
  self.uc.emu_start(0x272b8,0x27300,timeout=2000000,count=300)
  assert self.uc.reg_read(UC_ARM64_REG_PC)==0x27300;self.calls+=1;return self.read(OUT+32,'<f')[0]
 def configure(self,compensate,reference,zero,factor):
  self.write(INPUT,'<Q',INDEX);self.write(INPUT+16,'<Q',LAYER);self.write(LAYER,'<Q',TUNING);self.write(INPUT+56,'<Q',TABLE)
  self.write(TUNING+40,'<I2f',int(compensate),reference,factor);self.write(TABLE+32,'<f',zero);self.write(OBJECT+16,'<fI',0.,0)
  self.write(OBJECT+8,'<Q',MANAGER)
 def lux(self,index,luma,reset=False):
  self.write(INDEX,'<f',index);self.write(INPUT+76,'<I',int(reset));self.begin=0x4b088;self.call(x1=INPUT,s0=luma)
  return self.read(OBJECT+16,'<f')[0]
 def cells(self,index,values,reset=False):
  assert len(values)==256
  for i,v in enumerate(values):self.write(CELLS+i*8,'<2f',v,0.)
  self.write(INDEX,'<f',index);self.write(INPUT+28,'<I',0);self.write(INPUT+76,'<I',int(reset));self.begin=0x4aee0
  self.uc.reg_write(UC_ARM64_REG_X2,OUT);self.call(x1=INPUT)
  return self.read(OUT,'<2f')
