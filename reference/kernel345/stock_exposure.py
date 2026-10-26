"""Run the retained exposure-table lookup instructions with math/log stubs."""
from pathlib import Path
import ctypes,math,struct,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'kernel329'))
from stock_emulator import StockMath,OBJECT,OUT,LOGGER
from unicorn.arm64_const import UC_ARM64_REG_S0,UC_ARM64_REG_S1,UC_ARM64_REG_D0,UC_ARM64_REG_X0,UC_ARM64_REG_X2,UC_ARM64_REG_PC,UC_ARM64_REG_LR
TABLE=OBJECT+0x1000;KNEES=OBJECT+0x2000

class StockExposure(StockMath):
 def __init__(self,path):
  super().__init__(path,0x2d9a0,0x2dbd8)
  self.libm=ctypes.CDLL('libm.so.6');self.libm.powf.argtypes=[ctypes.c_float,ctypes.c_float];self.libm.powf.restype=ctypes.c_float
  self.pow_calls=0;self.write(0x5bcb0,'<Q',LOGGER)
 def _step(self,uc,pc,size,user):
  if pc in [0x587e0,0x58740,0x586f0,LOGGER]:
   if pc==0x587e0:
    values=[struct.unpack('<f',struct.pack('<I',uc.reg_read(r)))[0] for r in [UC_ARM64_REG_S0,UC_ARM64_REG_S1]]
    value=self.libm.powf(*values);uc.reg_write(UC_ARM64_REG_S0,struct.unpack('<I',struct.pack('<f',value))[0]);self.pow_calls+=1
   elif pc==0x58740:
    value=struct.unpack('<d',struct.pack('<Q',uc.reg_read(UC_ARM64_REG_D0)))[0]
    assert value>0 and math.isfinite(value)
    uc.reg_write(UC_ARM64_REG_D0,struct.unpack('<Q',struct.pack('<d',math.log10(value)))[0])
   else:uc.reg_write(UC_ARM64_REG_X0,0);self.stub_calls+=1
   uc.reg_write(UC_ARM64_REG_PC,uc.reg_read(UC_ARM64_REG_LR));return
  if not any(a<=pc<b for a,b in [(0x2d9a0,0x2dbd8),(0x2d178,0x2d350)]):raise RuntimeError('Unexpected exposure path '+hex(pc))
  super()._step(uc,pc,size,user)
 def setup(self,knees):
  self.write(OBJECT,'<Q',TABLE)
  for address in [TABLE,OBJECT+8]:self.write(address,'<fI8xQ',1.,len(knees),KNEES)
  for i,knee in enumerate(knees):self.write(KNEES+i*24,'<f4xQIf',knee['gain'],knee['time'],knee['priority'],knee['index'])
 def lookup(self,knees,index,active=False):
  self.setup(knees);self.begin=0x2d9a0
  self.uc.mem_write(OUT,b'\0'*32);self.write(OUT+16,'<f',index);self.uc.reg_write(UC_ARM64_REG_X2,OUT)
  self.call(x1=int(active))
  return self.read(OUT,'<f')[0],self.read(OUT+8,'<Q')[0],self.read(OUT+16,'<f')[0]
 def frame_knee(self,knees,maximum_ns):
  self.setup(knees);self.write(OBJECT+1328,'<Q',maximum_ns);self.begin=0x2d178;self.call(x1=0)
  return self.read(OBJECT+1240,'<f')[0],self.read(OBJECT+1248,'<Q')[0],self.read(OBJECT+1256,'<I')[0],self.read(OBJECT+1260,'<f')[0]
