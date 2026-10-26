"""Instruction-only oracle for small retained OEM math functions.

No Android loader, native execution, file/network/device API or system call is
available to emulated code. Only the chosen function and logging stubs may run.
"""
from pathlib import Path
import struct
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_INTR
from unicorn.arm64_const import *

OBJECT=0x1000000;STACK=0x2000000;TLS=0x3000000
STOP=0x4000000;LOGGER=0x4001000;LOGGER_OBJECT=0x4002000
OUT=0x5000000

class StockMath:
 def __init__(self,path,begin,end):
  self.uc=Uc(UC_ARCH_ARM64,UC_MODE_ARM);self.begin=begin;self.end=end
  self.calls=0;self.instructions=0;self.stub_calls=0
  data=Path(path).read_bytes();self.uc.mem_map(0,0x100000)
  offset=struct.unpack_from('<Q',data,32)[0];stride,count=struct.unpack_from('<HH',data,54)
  self.segments=[]
  for i in range(count):
   kind,flags,off,va,pa,filesz,memsz,align=struct.unpack_from('<IIQQQQQQ',data,offset+i*stride)
   if kind==1:
    self.uc.mem_write(va,data[off:off+filesz]);self.segments.append((va,off,filesz))
  for address,length in [(OBJECT,0x100000),(STACK,0x10000),(TLS,0x1000),(STOP,0x3000),(OUT,0x1000)]:self.uc.mem_map(address,length)
  self.uc.mem_write(LOGGER,b'\xc0\x03\x5f\xd6')
  self.uc.mem_write(LOGGER_OBJECT,struct.pack('<Q',LOGGER))
  self.uc.mem_write(0x5fea0,struct.pack('<Q',LOGGER_OBJECT))
  self.uc.reg_write(UC_ARM64_REG_CPACR_EL1,3<<20)
  self.uc.reg_write(UC_ARM64_REG_TPIDR_EL0,TLS)
  self.uc.hook_add(UC_HOOK_CODE,self._step)
  self.uc.hook_add(UC_HOOK_INTR,self._interrupt)
 def _interrupt(self,uc,number,_):raise RuntimeError('Emulated system call/exception rejected: '+str(number))
 def _step(self,uc,pc,size,_):
  self.instructions+=1
  if pc in [0x37280,LOGGER]:
   self.stub_calls+=1;uc.reg_write(UC_ARM64_REG_X0,0);uc.reg_write(UC_ARM64_REG_PC,uc.reg_read(UC_ARM64_REG_LR));return
  if not self.begin<=pc<self.end:raise RuntimeError('Unexpected emulated code path: '+hex(pc))
  word=struct.unpack('<I',uc.mem_read(pc,4))[0]
  if word&0xffe0001f==0xd4000001:raise RuntimeError('SVC instruction rejected')
 def read(self,address,fmt):return struct.unpack(fmt,self.uc.mem_read(address,struct.calcsize(fmt)))
 def write(self,address,fmt,*values):self.uc.mem_write(address,struct.pack(fmt,*values))
 def call(self,x0=OBJECT,x1=OUT,s0=None,s1=None):
  self.uc.reg_write(UC_ARM64_REG_SP,STACK+0xf000)
  self.uc.reg_write(UC_ARM64_REG_LR,STOP)
  self.uc.reg_write(UC_ARM64_REG_X0,x0);self.uc.reg_write(UC_ARM64_REG_X1,x1)
  for register,value in [(UC_ARM64_REG_S0,s0),(UC_ARM64_REG_S1,s1)]:
   if value is not None:self.uc.reg_write(register,struct.unpack('<I',struct.pack('<f',value))[0])
  self.uc.emu_start(self.begin,STOP,timeout=2000000,count=20000)
  if self.uc.reg_read(UC_ARM64_REG_PC)!=STOP:raise RuntimeError('Math oracle did not return')
  self.calls+=1
 def fragment(self):
  self.uc.reg_write(UC_ARM64_REG_X19,OBJECT)
  self.uc.reg_write(UC_ARM64_REG_X25,OUT)
  self.uc.emu_start(self.begin,self.end,timeout=2000000,count=20000)
  if self.uc.reg_read(UC_ARM64_REG_PC)!=self.end:raise RuntimeError('Math fragment did not finish')
  self.calls+=1

def calibration_oracle(path,ccts,golden,unit,unit_ccts=None,engine=None):
 engine=engine or StockMath(path,0x9e30,0xa8fc);n=len(ccts)
 engine.write(OBJECT+0x47c90,'<II',1,n)
 engine.write(OBJECT+0x47c98,'<6f',*(list(ccts)+[0.]*(6-n)))
 engine.write(OBJECT+0x2ed,'<I',n)
 for i in range(n):
  engine.write(OBJECT+0x47cb0+i*8,'<2f',*golden[i])
  engine.write(OBJECT+0x2f1+i*16,'<II2f',1,int((unit_ccts or ccts)[i]),*unit[i])
 engine.call()
 return [list(engine.read(OBJECT+0x47cb0+i*8,'<2f')) for i in range(10)],engine

if __name__=='__main__':
 path=Path('/mnt/e/edk2-samurai-out/kernel328/stats-source/com.qti.stats.awb.so')
 engine=StockMath(path,0x9bc0,0x9d70)
 print('thresholds',engine.read(0x46260,'<13f'))
 print('interpolation rows',engine.read(0x463ac,'<18I'))
 result,engine=calibration_oracle(path,[6500,3900,2800,5000,2300],[[1.,1.]]*5,[[1.1,1.2],[1.3,1.4],[1.5,1.6],[1.7,1.8],[1.9,2.]] )
 print('synthetic calibration',result,'instructions',engine.instructions)
