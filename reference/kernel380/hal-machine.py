"""Bounded offline execution of retained target HAL routines; no phone access."""
from pathlib import Path
import hashlib,struct
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_INTR,UC_HOOK_MEM_INVALID
from unicorn.arm64_const import *
P=Path('/mnt/e/edk2-samurai-out/kernel380')
STACK=0x2000000;TLS=0x3000000;STOP=0x4000000;DATA=0x5000000;HEAP=0x6000000
class Machine:
 def __init__(self):
  raw=(P.parent/'kernel281/camera.qcom.so-private').read_bytes();assert hashlib.sha256(raw).hexdigest()=='e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde'
  phoff=struct.unpack_from('<Q',raw,32)[0];stride,count=struct.unpack_from('<HH',raw,54);segments=[struct.unpack_from('<II6Q',raw,phoff+i*stride) for i in range(count)]
  u=self.u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);maximum=(max(s[3]+s[6] for s in segments if s[0]==1)+4095)&~4095;u.mem_map(0,maximum)
  for kind,flags,off,va,pa,filesz,memsz,align in segments:
   if kind==1:u.mem_write(va,raw[off:off+filesz])
  for address,size in [(STACK,0x100000),(TLS,4096),(STOP,4096),(DATA,0x100000),(HEAP,0x1000000)]:u.mem_map(address,size)
  u.reg_write(UC_ARM64_REG_CPACR_EL1,3<<20);u.reg_write(UC_ARM64_REG_TPIDR_EL0,TLS)
  self.allocations={};self.cursor=HEAP;self.providers={};self.instructions=0;self.pcs=set();self.phase='new'
  u.hook_add(UC_HOOK_CODE,self.step);u.hook_add(UC_HOOK_INTR,self.interrupt);u.hook_add(UC_HOOK_MEM_INVALID,self.invalid)
 def interrupt(self,u,number,user):raise RuntimeError('Emulated exception '+str(number)+' at '+hex(u.reg_read(UC_ARM64_REG_PC)))
 def invalid(self,u,access,address,size,value,user):raise RuntimeError('Invalid memory '+hex(address)+' at '+hex(u.reg_read(UC_ARM64_REG_PC)))
 def step(self,u,pc,size,user):
  self.instructions+=1;self.pcs.add(pc)
  if pc<0x5b1000:return
  if pc>=0x5b4000:raise RuntimeError('Unexpected provider/code '+hex(pc))
  a=u.reg_read(UC_ARM64_REG_X0);b=u.reg_read(UC_ARM64_REG_X1);c=u.reg_read(UC_ARM64_REG_X2);result=a
  self.providers[hex(pc)]=self.providers.get(hex(pc),0)+1
  if pc==0x5b1250:u.mem_write(a,bytes([b&255])*c)
  elif pc==0x5b1290:u.mem_write(a,bytes(u.mem_read(b,c)))
  elif pc==0x5b13e0:
   left=bytes(u.mem_read(a,c));right=bytes(u.mem_read(b,c));result=next((x-y for x,y in zip(left,right) if x!=y),0)&0xffffffffffffffff
  elif pc==0x5b13c0:
   assert 0<a<0x800000;result=self.cursor;self.cursor+=(a+31)&~31;assert self.cursor<HEAP+0x1000000
   self.allocations[result]=a;u.mem_write(result,bytes([0xa5])*a)
  elif pc==0x5b13d0:
   if a:assert a in self.allocations;del self.allocations[a]
   result=0
  else:raise RuntimeError('Unexpected provider '+hex(pc)+' phase '+self.phase)
  u.reg_write(UC_ARM64_REG_X0,result);u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR))
 def call(self,entry,*arguments,phase='call'):
  self.phase=phase
  for index,value in enumerate(arguments):self.u.reg_write(UC_ARM64_REG_X0+index,value)
  self.u.reg_write(UC_ARM64_REG_LR,STOP);self.u.reg_write(UC_ARM64_REG_SP,STACK+0xf0000)
  self.u.emu_start(entry,STOP,timeout=15000000,count=3000000)
  assert self.u.reg_read(UC_ARM64_REG_PC)==STOP,('Incomplete call',hex(self.u.reg_read(UC_ARM64_REG_PC)))
  return self.u.reg_read(UC_ARM64_REG_X0)&0xffffffff
 def read32(self,address):return struct.unpack('<I',self.u.mem_read(address,4))[0]
 def read64(self,address):return struct.unpack('<Q',self.u.mem_read(address,8))[0]
