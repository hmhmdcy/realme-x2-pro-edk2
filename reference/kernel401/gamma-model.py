"""Execute original Gamma LUT, WriteDMI and nested relocation routines."""
from pathlib import Path
import importlib.util,struct
from unicorn.arm64_const import *
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('hal380',HERE.parent/'kernel380/hal-machine.py');h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
DATA=h.DATA
class Gamma(h.Machine):
 def __init__(self):super().__init__();self.pending=0
 def step(self,u,pc,size,user):
  if pc in [0x4cd8b0,0x4cda68]:
   self.instructions+=1;self.providers[hex(pc)]=self.providers.get(hex(pc),0)+1;obj=DATA+0xa000
   assert u.reg_read(UC_ARM64_REG_X0)==obj
   if pc==0x4cd8b0:
    assert not self.pending and u.reg_read(UC_ARM64_REG_W1)==3;self.pending=3;result=DATA+0xb000+self.read32(obj+96)*4
   else:
    assert self.pending;u.mem_write(obj+96,struct.pack('<I',self.read32(obj+96)+self.pending));self.pending=0;result=0
   u.reg_write(UC_ARM64_REG_X0,result);u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR));return
  return super().step(u,pc,size,user)
 def lut(self,curve):
  self.u.mem_write(DATA,struct.pack('<I257f',0,*curve));self.u.mem_write(DATA+0x2000,bytes(1056))
  for r,v in [(UC_ARM64_REG_SP,h.STACK+0xf0000),(UC_ARM64_REG_X9,DATA),(UC_ARM64_REG_X15,0),(UC_ARM64_REG_X23,DATA+0x2000)]:self.u.reg_write(r,v)
  self.u.emu_start(0x355148,0x35528c,timeout=1000000,count=20000);assert self.u.reg_read(UC_ARM64_REG_PC)==0x35528c
  assert not any(bytes(self.u.mem_read(DATA+0x2400,32)));return bytes(self.u.mem_read(DATA+0x2000,1024))
 def headers(self,iova,enabled=1):
  cmd=DATA+0xa000;payload=DATA+0xb000;nested=DATA+0xc000;lutcmd=DATA+0xa800;obj=DATA+0x20000;inp=DATA+0x22000;array=DATA+0x28000;iq=DATA+0x30000
  for p,n in [(cmd,256),(lutcmd,256),(nested,256),(obj,1024),(inp,0x5000),(array,128),(iq,2584)]:self.u.mem_write(p,bytes(n))
  self.u.mem_write(payload,bytes(36)+bytes([0xa7])*32)
  self.u.mem_write(cmd+116,b'\x01');self.u.mem_write(cmd+120,struct.pack('<IIQ',8,0,nested));self.u.mem_write(lutcmd+100,struct.pack('<I',3))
  self.u.mem_write(obj+12,struct.pack('<I',enabled));self.u.mem_write(obj+168,struct.pack('<Q3I',lutcmd,0,1024,2048))
  self.u.mem_write(inp+2584,struct.pack('<Q',iq));self.u.mem_write(inp+2600,struct.pack('<Q',array));self.u.mem_write(array+40,struct.pack('<Q',cmd))
  for r,v in [(UC_ARM64_REG_SP,h.STACK+0xf0000),(UC_ARM64_REG_X25,obj),(UC_ARM64_REG_X27,inp)]:self.u.reg_write(r,v)
  self.u.emu_start(0x35242c,0x3524cc,timeout=1000000,count=10000);assert self.u.reg_read(UC_ARM64_REG_PC)==0x3524cc
  assert self.read32(iq+2192)==enabled and not self.pending
  assert bytes(self.u.mem_read(payload+36,32))==bytes([0xa7])*32
  if not enabled:
   assert not self.read32(cmd+96) and not self.read32(cmd+124);return b''
  assert self.read32(cmd+96)==9 and self.read32(cmd+124)==3
  raw=bytearray(self.u.mem_read(payload,36))
  for i in range(3):
   dest,is_nested,source_offset,pad,source=struct.unpack('<4IQ',self.u.mem_read(nested+24*i,24))
   assert (dest,is_nested,source_offset,pad,source)==(4+12*i,1,1024*i,0,lutcmd)
   assert struct.unpack_from('<3I',raw,12*i)==(0x0a0003ff,0,0x6008|((i+1)<<24))
   # Device-address materialization of the actual relocation record. Only the
   # three trusted in-page LUT offsets are accepted; no packet/math is stubbed.
   struct.pack_into('<I',raw,dest,iova+source_offset)
  return bytes(raw)
