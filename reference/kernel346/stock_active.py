from pathlib import Path
import math,struct,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'kernel345'))
from stock_exposure import StockExposure
from stock_emulator import StockMath,OBJECT
from unicorn.arm64_const import UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_D0,UC_ARM64_REG_LR,UC_ARM64_REG_PC
ACTIVE=OBJECT+0x6000

class StockActive(StockExposure):
 def _step(self,uc,pc,size,user):
  if pc in [0x58720,0x58820]:
   if pc==0x58720:
    dest,source,count=[uc.reg_read(r) for r in [UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2]]
    if count:uc.mem_write(dest,bytes(uc.mem_read(source,count)))
    uc.reg_write(UC_ARM64_REG_X0,dest)
   else:
    value=struct.unpack('<d',struct.pack('<Q',uc.reg_read(UC_ARM64_REG_D0)))[0]
    uc.reg_write(UC_ARM64_REG_D0,struct.unpack('<Q',struct.pack('<d',math.exp2(value)))[0])
   uc.reg_write(UC_ARM64_REG_PC,uc.reg_read(UC_ARM64_REG_LR));return
  if 0x2d350<=pc<0x2d9a0:
   StockMath._step(self,uc,pc,size,user);return
  super()._step(uc,pc,size,user)
 def program(self,knees,maximum_ns,ev,cap_enabled,maximum_gain,hdr3):
  self.setup(knees);self.write(OBJECT+24,'<Q',ACTIVE)
  self.write(OBJECT+1320,'<f',ev);self.write(OBJECT+1328,'<Q',maximum_ns)
  self.write(OBJECT+1336,'<If',int(cap_enabled),maximum_gain);self.write(OBJECT+1348,'<I',int(hdr3))
  for address in [0x2d178,0x2d350,0x2d508]:
   self.begin=address;self.call(x1=0)
  count=self.read(OBJECT+12,'<I')[0];assert count<=len(knees)+2
  read_knee=lambda at:(self.read(at,'<f')[0],self.read(at+8,'<Q')[0],self.read(at+16,'<I')[0],self.read(at+20,'<f')[0])
  return dict(frame=read_knee(OBJECT+1240),ev=read_knee(OBJECT+1264),offset=self.read(OBJECT+1344,'<f')[0],
   knees=[read_knee(ACTIVE+i*24) for i in range(count)])
