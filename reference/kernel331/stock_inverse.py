"""Restricted instruction oracle for the retained OEM inverse CCT path."""
from pathlib import Path
import math, struct, sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'kernel329'))
from stock_emulator import StockMath, OBJECT, OUT, LOGGER
from unicorn.arm64_const import *

SOLVER=OBJECT+0xe8000; FRAME=OBJECT+0xe9000; POINTS=OUT+0x800

class StockInverse(StockMath):
 def __init__(self,path):
  self.allowed=[(0x9d70,0x9e30),(0x8380,0x8420),(0x6f00,0x6f4c),(0x6f98,0x6fac),
   (0x6dc8,0x6dd8),(0x7d20,0x7d64),(0x260f8,0x26ae0),(0x25da0,0x25ef0)]
  self.visited=set();self.copy_calls=0;self.sqrt_calls=0
  super().__init__(path,0x260f8,0x264c0)
  self.write(OBJECT,'<Q',0x5ecb8)
  self.write(OBJECT+0xde6b8,'<Q',SOLVER)
  self.write(OBJECT+0xde6e8,'<Q',FRAME)
  self.write(SOLVER,'<Q',0x5f750)
  self.write(SOLVER+240,'<QQ',POINTS,OBJECT)
 def _step(self,uc,pc,size,_):
  self.instructions+=1;self.visited.add(pc)
  if pc in [0x37280,LOGGER,0x54c0,0x54a0]:
   if pc==0x54c0:
    dst,src,n=[uc.reg_read(r) for r in [UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2]]
    assert n<=128
    uc.mem_write(dst,bytes(uc.mem_read(src,n)));self.copy_calls+=1
   elif pc==0x54a0:
    value=struct.unpack('<f',struct.pack('<I',uc.reg_read(UC_ARM64_REG_S0)))[0]
    result=math.sqrt(value) if value>=0 else float('nan')
    uc.reg_write(UC_ARM64_REG_S0,struct.unpack('<I',struct.pack('<f',result))[0]);self.sqrt_calls+=1
   else:self.stub_calls+=1;uc.reg_write(UC_ARM64_REG_X0,0)
   uc.reg_write(UC_ARM64_REG_PC,uc.reg_read(UC_ARM64_REG_LR));return
  if not any(a<=pc<b for a,b in self.allowed):raise RuntimeError('Unexpected inverse path '+hex(pc))
  word=struct.unpack('<I',uc.mem_read(pc,4))[0]
  if word&0xffe0001f==0xd4000001:raise RuntimeError('SVC instruction rejected')
 def configure(self,points):
  self.write(OBJECT+0x91e,'<20f',*[v for p in points for v in p])
  self.begin=0x260f8
  self.call(x0=SOLVER,x1=FRAME)
 def estimate(self,ratio):
  self.begin=0x9d70
  self.call(s0=ratio[0],s1=ratio[1])
  result=self.read(FRAME+44,'<2fI')
  assert self.read(OUT,'<f')[0]==result[1]
  return result
 def calibrated_points(self,points,factors):
  auxiliary=OBJECT+0xea000
  self.write(auxiliary+32,'<QQ',OBJECT+0x289,POINTS)
  self.write(OUT+32,'<20f',*[v for p in points for v in p])
  self.write(OBJECT+0x47cb0,'<20f',*[v for p in factors for v in p])
  self.uc.reg_write(UC_ARM64_REG_X0,OUT)
  self.uc.reg_write(UC_ARM64_REG_X19,auxiliary)
  self.uc.emu_start(0x25da0,0x25ef0,timeout=2000000,count=1000)
  assert self.uc.reg_read(UC_ARM64_REG_PC)==0x25ef0
  return [list(self.read(OBJECT+0x91e+i*8,'<2f')) for i in range(10)]
