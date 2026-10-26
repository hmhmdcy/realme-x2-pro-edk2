"""Bounded target GTM calculation; only C library operations are provided."""
from pathlib import Path
import ctypes,importlib.util,json,struct
from unicorn.arm64_const import *
from unicorn import UC_HOOK_MEM_WRITE
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('parser426gtm',HERE.parent/'kernel426/ds4-model.py');n=importlib.util.module_from_spec(s);s.loader.exec_module(n);h=n.h
libm=ctypes.CDLL('libm.so.6')
math_calls={0x5b1960:('powf',2,False),0x5b1980:('expf',1,False),0x5b12c0:('logf',1,False),0x5b1320:('log',1,True),0x5b1990:('exp2f',1,False)}
for name,count,double in math_calls.values():
 f=getattr(libm,name);kind=ctypes.c_double if double else ctypes.c_float;f.argtypes=[kind]*count;f.restype=kind
class Machine(n.Machine):
 def __init__(self,packing_selector=2,swap=False):
  super().__init__()
  # Explicit offline platform fixture, not a readout from the connected phone.
  # Keep original GetInstance and every GTM instruction; skip device discovery
  # through its ordinary already-initialized state, exercising each pack branch.
  assert packing_selector in [0,2,3]
  self.u.mem_write(0x96aac0+0x6a0,b'\1');self.u.mem_write(0x60e3d8+0xcdca4,struct.pack('<I',3))
  platform=h.DATA+0xe0000;settings=h.DATA+0xe1000
  self.u.mem_write(platform,bytes(64));self.u.mem_write(platform+16,struct.pack('<I',packing_selector));self.u.mem_write(0x96aac0+1736,struct.pack('<Q',platform))
  self.u.mem_write(settings,bytes(64));self.u.mem_write(settings+16,struct.pack('<3I',int(swap),int(swap),int(swap)));self.u.mem_write(0x60e3d8+0x189fb0,struct.pack('<Q',settings))
  self.lut_writes=set();self.u.hook_add(UC_HOOK_MEM_WRITE,self.check_write)
 def check_write(self,u,access,address,size,value,user):
  assert address>=0x5b4000,('Attempted write into read-only target text/data',hex(address),hex(u.reg_read(UC_ARM64_REG_PC)))
  lut=h.DATA+0x12000
  self.lut_writes.update(range(max(address,lut),min(address+size,lut+512)))
 def step(self,u,pc,size,user):
  if pc==0x37d298:self.adrc_gain=bytes(u.mem_read(u.reg_read(UC_ARM64_REG_SP)+0x430,260))
  if pc in math_calls:
   self.instructions+=1;self.pcs.add(pc);self.providers[hex(pc)]=self.providers.get(hex(pc),0)+1
   name,count,double=math_calls[pc];register=UC_ARM64_REG_D0 if double else UC_ARM64_REG_S0;fmt,integer=('d','Q') if double else ('f','I')
   values=[struct.unpack('<'+fmt,struct.pack('<'+integer,u.reg_read(register+i)))[0] for i in range(count)];value=getattr(libm,name)(*values)
   u.reg_write(register,struct.unpack('<'+integer,struct.pack('<'+fmt,value))[0]);u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR));return
  super().step(u,pc,size,user)
 def load_parsed(self,path):
  record=json.loads(Path(path).read_text());addresses=[]
  for address,content in record['allocations'].items():
   at=int(address,16);raw=bytes.fromhex(content);self.u.mem_write(at,raw);self.allocations[at]=len(raw);addresses.append(at)
  self.cursor=max(a+self.allocations[a]+32 for a in addresses)
  return min(addresses)+88,record
 def calculate(self,chromatix,*,sensitivity=1.0,drc_gain=1.0,lux=100.0,gain=1.0,adrc=None,histogram=None,request=0,bank=0):
  assert bank in [0,1]
  u=self.u;inp=h.DATA+0x10000;out=h.DATA+0x11000;lut=h.DATA+0x12000;interpolation=h.DATA+0x14000;tmc=h.DATA+0x16000;adrc_at=h.DATA+0x17000;hist_at=h.DATA+0x19000
  u.mem_write(inp,bytes(0x10000));u.mem_write(inp,struct.pack('<Q',chromatix));u.mem_write(inp+40,bytes([bank]))
  for off,value in [(12,drc_gain),(16,1.0),(20,sensitivity),(24,1.0),(28,lux),(32,1.0),(36,gain)]:u.mem_write(inp+off,struct.pack('<f',value))
  reg=out+0x800;u.mem_write(inp+128,struct.pack('<Q',interpolation));u.mem_write(out,struct.pack('<I4xQQ',0,reg,lut));u.mem_write(reg,struct.pack('<I',0xa6a6a6a6));u.mem_write(lut,bytes([0xa7])*544)
  if adrc is not None:
   assert len(adrc)==4240 and struct.unpack_from('<I',adrc,4)[0]==1;u.mem_write(adrc_at,adrc);u.mem_write(tmc+24,struct.pack('<I',1));u.mem_write(tmc+32,struct.pack('<Q',adrc_at))
  if histogram is not None:
   assert len(histogram)==4096;u.mem_write(hist_at,histogram);u.mem_write(inp+48,struct.pack('<Q',hist_at));u.mem_write(inp+112,struct.pack('<QI',request,4))
  self.adrc_gain=None;self.lut_writes=set();result=self.call(0x37c818,inp,0,out,tmc,phase='whole-target-gtm-calculation')
  assert result==0,('GTM calculation result',result)
  assert bytes(u.mem_read(lut+512,32))==bytes([0xa7])*32
  assert len(self.lut_writes)==512 and self.read32(reg)==(0xa6a6a6a6|bank)
  if adrc is not None:assert bytes(u.mem_read(adrc_at,4240))==adrc and self.read64(inp+104)==adrc_at
  return bytes(u.mem_read(lut,512)),bytes(u.mem_read(inp,136)),bytes(u.mem_read(interpolation,360))
