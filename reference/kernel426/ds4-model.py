"""Target native DS4 parser, register calculation and transport recorder."""
from pathlib import Path
import importlib.util,struct
from unicorn.arm64_const import *
from unicorn import UC_HOOK_MEM_READ
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('hal380',HERE.parent/'kernel380/hal-machine.py');h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
class Machine(h.Machine):
 def __init__(self):
  super().__init__();self.writes=[];self.selected_module=None;self.selections=[];self.trace_root=None;self.calibration_reads=[]
  self.u.hook_add(UC_HOOK_MEM_READ,self.read_calibration)
 def read_calibration(self,u,access,address,size,value,user):
  if self.trace_root is not None and self.trace_root<=address<self.trace_root+200:self.calibration_reads.append((address-self.trace_root,size))
 def string(self,p):
  raw=bytes(self.u.mem_read(p,512));assert b'\0' in raw;return raw.split(b'\0',1)[0]
 def step(self,u,pc,size,user):
  if pc==0x52cb10:
   a,b,c,d=[u.reg_read(UC_ARM64_REG_X0+i) for i in range(4)];assert c<=64
   self.writes.append((b,bytes(u.mem_read(d,c*4))));u.reg_write(UC_ARM64_REG_X0,0);u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR));return
  if pc==0x176e18 and self.selected_module is not None:
   self.selections.append(self.string(u.reg_read(UC_ARM64_REG_X1)).decode());u.reg_write(UC_ARM64_REG_X0,self.selected_module);u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR));return
  if pc in [0x5b14a0,0x5b1580,0x5b1550,0x5b15d0,0x5b15e0,0x5b1470]:
   self.instructions+=1;self.pcs.add(pc);self.providers[hex(pc)]=self.providers.get(hex(pc),0)+1
   a,b,c=[u.reg_read(UC_ARM64_REG_X0+i) for i in range(3)];result=0
   if pc==0x5b14a0:
    assert b>=8 and not b&(b-1) and 0<c<0x100000
    address=(self.cursor+b-1)&~(b-1);self.cursor=address+((c+31)&~31);assert self.cursor<h.HEAP+0x1000000
    self.allocations[address]=c;u.mem_write(address,bytes([0xa5])*c);u.mem_write(a,struct.pack('<Q',address))
   elif pc==0x5b1580:
    left,right=self.string(a),self.string(b);result=0 if left==right else 1 if left>right else 0xffffffffffffffff
   elif pc==0x5b15e0:
    left,right=self.string(a)[:c].lower(),self.string(b)[:c].lower();result=0 if left==right else 1 if left>right else 0xffffffffffffffff
   elif pc==0x5b1550:result=len(self.string(a))
   elif pc==0x5b15d0:
    raw=self.string(b);result=len(raw)
    if c:u.mem_write(a,raw[:c-1]+b'\0')
   elif pc==0x5b1470:result=0
   u.reg_write(UC_ARM64_REG_X0,result);u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR));return
  super().step(u,pc,size,user)
 def parse(self,tag,uid,data,revision_uid,revision):
  D=h.DATA;prototype=D+0x1000;table=D+0x2000;entries=D+0x3000
  self.u.mem_write(D,bytes(0x10000));self.u.mem_write(prototype+16,tag.encode()+b'\0');self.u.mem_write(prototype+56,struct.pack('<Q',1))
  self.u.mem_write(table,struct.pack('<I',2));self.u.mem_write(table+16,struct.pack('<Q',entries))
  for i,(entry_uid,name,payload) in enumerate([(uid,tag,data),(revision_uid,'revision',revision)]):
   p=entries+i*88;at=D+0x8000+i*0x1000
   self.u.mem_write(p,struct.pack('<QI',table,entry_uid));self.u.mem_write(p+12,name.encode()+b'\0');self.u.mem_write(p+45,struct.pack('<Q',1))
   self.u.mem_write(p+68,struct.pack('<IQQ',len(payload),at,0));self.u.mem_write(at,payload)
  result=self.call(0x1fcdf0,prototype,0,entries,8,phase='whole-ds4-target-parse');assert result
  assert self.read64(entries+80)==len(data),(self.read64(entries+80),len(data))
  return result,bytes(self.u.mem_read(result,200))
 def registers(self,parsed,height,path=2,seed=0):
  D=h.DATA;obj=D+0x10000;state=D+0x11000;inp=D+0x12000
  self.u.mem_write(obj,bytes(256));self.u.mem_write(state,bytes(256));self.u.mem_write(inp,bytes(20032))
  previous=[seed]*12 if isinstance(seed,int) else list(seed[:3])+[0]*9
  self.u.mem_write(obj+48,struct.pack('<12I',*previous));self.u.mem_write(obj+96,struct.pack('<QI',state,path))
  self.u.mem_write(obj+112,struct.pack('<QQ',parsed+88,parsed+88));self.u.mem_write(state+4,struct.pack('<I',height))
  self.trace_root=parsed;self.calibration_reads=[]
  self.call(0x31d130,obj,inp,phase='whole-target-ds4-register-calculation')
  self.trace_root=None
  assert self.calibration_reads==[(140,4),(144,4),(148,4)]
  offset={2:48,3:60,5:72,6:84}[path]
  return bytes(self.u.mem_read(obj+offset,12))
 def packed(self,parsed,height,previous):
  regs=self.registers(parsed,height,seed=previous)
  D=h.DATA;obj=D+0x70000;inp=D+0x12000;calculated=D+0x80000
  self.u.mem_write(obj,bytes(256));self.u.mem_write(calculated,bytes(4096))
  self.u.mem_write(obj+48,struct.pack('<I',previous[3]));self.u.mem_write(obj+68,struct.pack('<I',2))
  self.u.mem_write(inp+80,struct.pack('<Q',D+0x90000));self.u.mem_write(inp+2528,struct.pack('<Q',calculated))
  before=len(self.writes);assert self.call(0x331e78,obj,inp,phase='whole-target-r2pd-execute')==0
  assert len(self.writes)==before+1 and self.writes[-1][0]==0xd6c
  assert self.read32(calculated+968)==0x4000
  return regs+self.writes[-1][1]
 def execute(self,parsed,width,height):
  D=h.DATA;create=D+0x10000;inp=D+0x20000;cfg=D+0x30000;calculated=D+0x40000;outer=D+0x50000
  self.u.mem_write(create,bytes(0x50000));self.u.mem_write(create+20,struct.pack('<I',2))
  assert self.call(0x31c5b0,create,phase='whole-target-ds4-create')==0
  obj=self.read64(create);assert obj
  for at,value in [(80,D+0x61000),(2520,cfg),(2528,calculated),(2760,outer),(2840,D+0x54000)]:self.u.mem_write(inp+at,struct.pack('<Q',value))
  for at,value in [(outer,D+0x51000),(D+0x51000,D+0x52000),(D+0x52000+1088,D+0x53000)]:self.u.mem_write(at,struct.pack('<Q',value))
  qw,qh=((width+7)//4)&~1,((height+7)//4)&~1
  self.u.mem_write(cfg+200,struct.pack('<2I',qw,qh));self.u.mem_write(calculated+104,struct.pack('<2I',width,height))
  self.u.mem_write(calculated+0x2c78,struct.pack('<4I',0,0,width-1,height-1));self.u.mem_write(D+0x54000,struct.pack('<I',1))
  self.selected_module=parsed;before=len(self.writes)
  assert self.call(0x31c7b8,obj,inp,phase='whole-target-ds4-execute')==0
  self.selected_module=None
  writes=self.writes[before:];assert len(writes)==1 and writes[0][0]==0xd60
  assert self.read64(obj+112)==parsed+88
  return writes[0][1],self.read32(calculated+968),bytes(self.u.mem_read(obj,128))
 def producer_crops_and_round(self,width,height):
  D=h.DATA;inp=D+0x20000;calculated=D+0x40000;obj=D+0xa0000
  self.u.mem_write(obj,bytes(512));self.u.mem_write(obj+12,struct.pack('<I',1));self.u.mem_write(obj+112,struct.pack('<I',2))
  self.u.mem_write(calculated+0x2c78,struct.pack('<8I',0,0,width-1,height-1,0,0,width//2-1,height//2-1))
  before=len(self.writes);assert self.call(0x330e50,obj,inp,phase='whole-target-ds4-precrop-execute')==0
  crop=self.writes[before:];assert [a for a,b in crop]==[0xd84,0xda4]
  obj=D+0xa0200;self.u.mem_write(obj,bytes(256));self.u.mem_write(obj+176,struct.pack('<2I',2,2))
  self.u.mem_write(inp+2484,struct.pack('<I',18));self.u.mem_write(inp+19896,struct.pack('<I',1))
  before=len(self.writes);assert self.call(0x332618,obj,inp,phase='whole-target-ds4-round-clamp-execute')==0
  rounding=self.writes[before:]
  obj=D+0xa0400;self.u.mem_write(obj,bytes(256));self.u.mem_write(obj+68,struct.pack('<I',2))
  before=len(self.writes);assert self.call(0x331e78,obj,inp,phase='whole-target-ds4-pack-execute')==0
  packing=self.writes[before:]
  return crop,rounding,packing,self.read32(calculated+968)
