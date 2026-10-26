"""Execute retained target LTM fragments with only command storage providers."""
from pathlib import Path
import importlib.util,struct
from unicorn.arm64_const import *
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('gamma402',HERE.parent/'kernel402/gamma-model.py');g=importlib.util.module_from_spec(s);s.loader.exec_module(g)
h=g.h;DATA=h.DATA
class LTM(g.Gamma):
 def initialize(self):
  obj=DATA+0x20000;self.u.mem_write(obj,bytes(1168));self.u.mem_write(obj+440,struct.pack('<Q',DATA+0x40000));self.u.reg_write(UC_ARM64_REG_X0,obj);self.u.reg_write(UC_ARM64_REG_X29,h.STACK+0xe0000)
  self.u.emu_start(0x35e658,0x35e6a8,count=1000);assert self.u.reg_read(UC_ARM64_REG_PC)==0x35e6a8
  offsets=struct.unpack('<13I',self.u.mem_read(obj+568,52));assert offsets==(0,48,304,560,816,1072,1328,1392,1456,1712,1968,2224,2480)
  return obj,offsets
 def resource(self):
  resource=DATA+0x50000;node=DATA+0x60000;inp=DATA+0x70000;params=DATA+0x78000;array=DATA+0x79000
  for address,size in [(resource,56),(node,1168),(inp,0x6000),(params,16),(array,128)]:self.u.mem_write(address,bytes(size))
  self.u.mem_write(params,struct.pack('<Q',array));self.u.mem_write(inp+19844,struct.pack('<I',4))
  for reg,value in [(UC_ARM64_REG_X22,resource),(UC_ARM64_REG_X20,node),(UC_ARM64_REG_X21,inp),(UC_ARM64_REG_X19,params),(UC_ARM64_REG_SP,h.STACK+0xe0000)]:self.u.reg_write(reg,value)
  self.u.emu_start(0x36717c,0x3671f0,count=1000);assert self.u.reg_read(UC_ARM64_REG_PC)==0x3671f0
  assert self.read32(resource)==3296 and self.read32(resource+32)==1
  return self.read32(resource),self.read32(resource+32)
 def headers(self,iova,enabled=1):
  resource,kind=self.resource();obj,offsets=self.initialize();cmd=DATA+0xa000;payload=DATA+0xb000;nested=DATA+0xc000;lutcmd=DATA+0xa800;inp=DATA+0x22000;array=DATA+0x28000
  for p,n in [(cmd,256),(lutcmd,256),(nested,1024),(inp,0x5000),(array,128)]:self.u.mem_write(p,bytes(n))
  self.u.mem_write(payload,bytes(156)+bytes([0xa7])*32);self.u.mem_write(cmd+116,b'\x01');self.u.mem_write(cmd+120,struct.pack('<IIQ',32,0,nested));self.u.mem_write(lutcmd+100,struct.pack('<I',kind))
  self.u.mem_write(obj+12,struct.pack('<I',enabled));self.u.mem_write(obj+560,struct.pack('<Q',lutcmd));self.u.mem_write(inp+2600,struct.pack('<Q',array));self.u.mem_write(array+40,struct.pack('<Q',cmd))
  for reg,value in [(UC_ARM64_REG_X26,obj),(UC_ARM64_REG_X24,inp),(UC_ARM64_REG_SP,h.STACK+0xe0000)]:self.u.reg_write(reg,value)
  self.u.emu_start(0x366840,0x3669e0,timeout=1000000,count=30000);assert self.u.reg_read(UC_ARM64_REG_PC)==0x3669e0
  assert bytes(self.u.mem_read(payload+156,32))==bytes([0xa7])*32 and not self.pending
  if not enabled:assert not self.read32(cmd+96) and not self.read32(cmd+124);return b'',offsets
  assert self.read32(cmd+96)==39 and self.read32(cmd+124)==13
  raw=bytearray(self.u.mem_read(payload,156));sizes=[48,256,256,256,256,256,64,64,256,256,256,256,256]
  for i,(off,size) in enumerate(zip(offsets,sizes)):
   dest,is_nested,src,pad,source=struct.unpack('<4IQ',self.u.mem_read(nested+24*i,24));assert (dest,is_nested,src,pad,source)==(4+12*i,1,off,0,lutcmd)
   assert struct.unpack_from('<3I',raw,12*i)==(0x01000000|(size-1),0,0x5c08|((i+1)<<24));struct.pack_into('<I',raw,dest,iova+off)
  return bytes(raw),offsets
 def inverse(self,nodes,cached=False):
  u=self.u;sp=h.STACK+0xe0000;obj=DATA+0x50000;out=DATA+0x60000;prev=DATA+0x62000;inverse=DATA+0x64000
  if not cached:
   u.mem_write(sp,bytes(0x4000));u.mem_write(obj,bytes(1168));u.mem_write(prev,bytes([0xff])*256);u.mem_write(inverse,bytes([0xa7])*256);u.mem_write(obj+152,struct.pack('<2Q',prev,inverse))
  u.mem_write(out,bytes([0xa7])*288);u.mem_write(sp+240,struct.pack('<Q',obj));u.mem_write(sp+536,struct.pack('<Q',out));u.mem_write(sp+9360,struct.pack('<64i',*nodes));u.reg_write(UC_ARM64_REG_SP,sp)
  u.emu_start(0x3618a4,0x362320,timeout=30000000,count=10000000);assert u.reg_read(UC_ARM64_REG_PC)==0x362320,hex(u.reg_read(UC_ARM64_REG_PC))
  assert bytes(u.mem_read(out+256,32))==bytes([0xa7])*32 and bytes(u.mem_read(prev,256))==struct.pack('<64i',*nodes)
  raw=bytes(u.mem_read(out,256));assert raw==bytes(u.mem_read(inverse,256));return raw
