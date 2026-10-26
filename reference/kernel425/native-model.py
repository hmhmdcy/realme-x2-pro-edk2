"""Retained HAL coarse-format and multipass striping, without hardware enqueue."""
from pathlib import Path
import importlib.util,struct
from unicorn.arm64_const import *
HERE=Path(__file__).resolve().parent
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
h=module('hal380',HERE.parent/'kernel380/hal-machine.py')
class Native(h.Machine):
 def pd10(self,width,height):
  D=h.DATA;fmt=D+0x10000;info=D+0x20000
  self.u.mem_write(fmt,bytes(512));self.u.mem_write(info,bytes(256));self.u.mem_write(fmt,struct.pack('<3I',width,height,18));self.u.mem_write(fmt+144,struct.pack('<Q',1))
  self.call(0x453ab8,fmt,info,1,phase='pd10-format-initialize')
  image=bytes(self.u.mem_read(fmt,176));config=D+0x30000;self.u.mem_write(config,bytes(1216))
  self.call(0x2e4b88,D+0x60000,config,fmt,1,0,phase='pd10-config-io')
  descriptor=bytes(self.u.mem_read(config+84,84))
  assert struct.unpack_from('<I',descriptor)[0]==10
  assert struct.unpack_from('<2I',descriptor,4)==(width,height)
  return image,descriptor
 def striping(self,config,width,height,cores,iq_blob):
  D=h.DATA;u=self.u;assert len(config)==1216
  u.mem_write(D,config);assert self.call(0x144348,D,0,0x10705,0x10000,D+0x2000,D+0x2010,D+0x2014,phase='multipass-create')==0
  context=self.read64(D+0x2000);capacity=self.read32(D+0x2010);bl=self.read32(D+0x2014)
  assert 0<capacity<0x20000
  out=D+0x40000;params=D+0x3000;iq=D+0x20000
  u.mem_write(params,struct.pack('<5QI',iq,D+0x12000,D+0x14000,D+0x16000,D+0x18000,cores))
  for target in [D+0x16000,D+0x18000]:u.mem_write(target,struct.pack('<6I',width,height,0,0,width,height))
  u.mem_write(iq,iq_blob);u.mem_write(out,bytes([0xa5])*(capacity+64))
  assert self.call(0x1448f0,context,params,out,D+0x70000,D+0x80000,phase='multipass-execute')==0
  raw=bytes(u.mem_read(out,capacity));passes=struct.unpack_from('<I',raw,20)[0]
  used=2268+624*sum(struct.unpack_from('<H',raw,428+412*i)[0] for i in range(passes))
  assert used<=capacity and bytes(u.mem_read(out+capacity,64))==bytes([0xa5])*64
  assert self.call(0x144988,D+0x2000,phase='multipass-destroy')==0 and not self.allocations
  return raw[:used],bl,capacity
