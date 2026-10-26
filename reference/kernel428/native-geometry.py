"""Use original FULL Crop output as the input to original DS4 PreCrop."""
from pathlib import Path
import importlib.util,struct
from unicorn import UC_HOOK_MEM_WRITE
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('base426',HERE.parent/'kernel426/ds4-model.py');base=importlib.util.module_from_spec(s);s.loader.exec_module(base);h=base.h
class Machine(base.Machine):
 def full_crop(self,width,height,input_width=None,input_height=None):
  iw,ih=input_width or width,input_height or height;D=h.DATA;inp=D+0x20000;cfg=D+0x30000;calculated=D+0x40000;create=D+0xb0000
  image_writes=[]
  def record(u,access,address,size,value,user):
   if address<0x1000000:image_writes.append((address,size))
  watch=self.u.hook_add(UC_HOOK_MEM_WRITE,record)
  self.u.mem_write(create,bytes(4096));self.u.mem_write(create+20,struct.pack('<I',0));self.u.mem_write(create+2552,struct.pack('<Q',cfg))
  assert self.call(0x315e88,create,phase='whole-original-full-crop-create')==0;obj=self.read64(create);assert obj
  for at,value in [(80,D+0x61000),(2520,cfg),(2528,calculated)]:self.u.mem_write(inp+at,struct.pack('<Q',value))
  self.u.mem_write(cfg,struct.pack('<4I',0,0,iw-1,ih-1));self.u.mem_write(cfg+32,struct.pack('<4I',0,0,iw,ih))
  self.u.mem_write(cfg+180,struct.pack('<2I',width,height));self.u.mem_write(cfg+13760,struct.pack('<I',0));self.u.mem_write(cfg+14096,struct.pack('<I',0))
  self.u.mem_write(inp+2480,struct.pack('<I',3));self.u.mem_write(inp+19896,struct.pack('<I',1))
  self.u.mem_write(calculated+104,struct.pack('<2I',width,height));self.u.mem_write(calculated+124,struct.pack('<2I',iw,ih));self.u.mem_write(calculated+144,struct.pack('<f',iw/width))
  before=len(self.writes);assert self.call(0x3161b0,obj,inp,phase='whole-original-full-crop-execute')==0
  self.u.hook_del(watch);assert not image_writes,image_writes
  data=bytes(self.u.mem_read(calculated+0x2c78,32));return data,self.writes[before:]
 def producer_crops_and_round(self,width,height):
  D=h.DATA;inp=D+0x20000;calculated=D+0x40000;obj=D+0xa0000
  self.produced_precrop,full_writes=self.full_crop(width,height)
  assert [a for a,b in full_writes]==[0xe10,0xe30]
  self.u.mem_write(obj,bytes(512));self.u.mem_write(obj+12,struct.pack('<I',1));self.u.mem_write(obj+112,struct.pack('<I',2))
  before=len(self.writes);assert self.call(0x330e50,obj,inp,phase='original-precrop-consuming-original-full-crop')==0;crop=self.writes[before:]
  obj=D+0xa0200;self.u.mem_write(obj,bytes(256));self.u.mem_write(obj+176,struct.pack('<2I',2,2))
  self.u.mem_write(inp+2484,struct.pack('<I',18));self.u.mem_write(inp+19896,struct.pack('<I',1))
  before=len(self.writes);assert self.call(0x332618,obj,inp,phase='original-ds4-round-clamp')==0;rounding=self.writes[before:]
  obj=D+0xa0400;self.u.mem_write(obj,bytes(256));self.u.mem_write(obj+68,struct.pack('<I',2))
  before=len(self.writes);assert self.call(0x331e78,obj,inp,phase='original-ds4-r2pd')==0;packing=self.writes[before:]
  return crop,rounding,packing,self.read32(calculated+968)
