"""Private offline providers for executing target configuration/geometry code."""
from pathlib import Path
import hashlib,json,struct
from collections import deque
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_HOOK_CODE,UC_HOOK_MEM_INVALID,UC_HOOK_INTR
from unicorn.arm_const import *
import host
P=host.PRIVATE;DATA=0x06000000;HEAP=0x05000000;STACK=0x02000000;STOP=0x04000000
class Machine:
 def __init__(self):
  raw=(P.parent/'kernel352/CAMERA_ICP.elf-private').read_bytes();assert hashlib.sha256(raw).hexdigest()=='a22bc8adbb4ae97e4f8d728eecb1fd19c1bf866250b0bb7e668951c41c159e63'
  phoff=struct.unpack_from('<I',raw,28)[0];stride,count=struct.unpack_from('<HH',raw,42);segs=[struct.unpack_from('<8I',raw,phoff+i*stride) for i in range(count)]
  self.u=u=Uc(UC_ARCH_ARM,UC_MODE_THUMB);u.mem_map(0,(max(s[2]+s[5] for s in segs if s[0]==1)+4095)&~4095)
  for kind,off,va,pa,n,size,flags,align in segs:
   if kind==1:u.mem_write(va,raw[off:off+n])
  for a,n in [(DATA,0x200000),(HEAP,0x200000),(STACK,0x100000),(STOP,4096),(0xe0040000,4096),(0xe0088000,4096)]:u.mem_map(a,n)
  self.write32(0xe0040000,0x10705);self.cursor=HEAP;self.allocated={};self.providers={};self.phase='new';self.payload=0;self.instructions=0;self.fault=None;self.recent=deque(maxlen=24);self.free_trace=[];self.packets=[];self.logs=[]
  self.stream=DATA+0x1000;self.context=DATA+0x2000;self.config=DATA+0x4000;self.reference=DATA+0x8000
  self.write32(self.stream+12,self.context);self.write32(self.context+8,self.config);self.write32(self.context+12,self.reference)
  u.hook_add(UC_HOOK_CODE,self.step);u.hook_add(UC_HOOK_MEM_INVALID,self.invalid);u.hook_add(UC_HOOK_INTR,self.interrupt)
 def write32(self,a,v):self.u.mem_write(a,struct.pack('<I',v))
 def read32(self,a):return struct.unpack('<I',self.u.mem_read(a,4))[0]
 def invalid(self,u,access,address,size,value,user):
  self.fault=dict(access=access,address=hex(address),bytes=size,pc=hex(u.reg_read(UC_ARM_REG_PC)));return False
 def interrupt(self,u,n,user):raise RuntimeError(f'Interrupt {n} PC {u.reg_read(UC_ARM_REG_PC):#x}')
 def allocate(self,n):
  assert 0<n<0x100000;v=self.cursor;self.cursor+=(n+31)&~31;assert self.cursor<HEAP+0x200000;self.allocated[v]=n;self.u.mem_write(v,bytes([0xa5])*n);return v
 def step(self,u,pc,size,user):
  self.instructions+=1
  self.recent.append(pc)
  if 0xf21e<=pc<0xf278:self.free_trace.append(hex(pc))
  if HEAP<=pc<HEAP+0x200000:raise RuntimeError('Execution left firmware at '+hex(pc)+' from '+str([hex(v) for v in self.recent]))
  a=u.reg_read(UC_ARM_REG_R0);b=u.reg_read(UC_ARM_REG_R1);c=u.reg_read(UC_ARM_REG_R2);result=0
  if pc==0xedd6:result=0x12345678
  elif pc==0x1a132:result=self.stream
  elif pc==0xe958:pass # Framework command retirement; no image logic.
  elif pc==0x1ba40:
   n=self.read32(b);assert 0<n<=4096;self.packets.append(bytes(u.mem_read(b,n)))
  elif pc==0xed48:result=0 # Empty failed-command history in the test stream.
  elif pc in [0x6cc0,0x6dbc]:result=self.allocate(a)
  elif pc in [0x6d14,0x6df8]:
   if a:assert a in self.allocated;del self.allocated[a]
  elif pc==0x25bf0:assert a>=0x100000;u.mem_write(a,bytes(u.mem_read(b,c)));result=a
  elif pc==0x25ef4:assert a>=0x100000;u.mem_write(a,bytes([b&255])*c);result=a
  elif pc==0x8316:
   fmt=u.reg_read(UC_ARM_REG_R3);self.logs.append(dict(caller=hex(u.reg_read(UC_ARM_REG_LR)),format=bytes(u.mem_read(fmt,256)).split(b'\0',1)[0].decode(errors='replace'),args=struct.unpack('<6I',u.mem_read(u.reg_read(UC_ARM_REG_SP),24))))
  elif pc==0x7e8e:raise RuntimeError(f'Firmware assertion {a:#x} {b:#x} {c} phase {self.phase}')
  else:return
  self.providers[hex(pc)]=self.providers.get(hex(pc),0)+1
  u.reg_write(UC_ARM_REG_R0,result);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def call(self,pc,*args,phase='call',stop=STOP):
  self.phase=phase
  if self.payload:self.write32(DATA+0xc000+4,self.payload)
  for i,v in enumerate(args):self.u.reg_write(UC_ARM_REG_R0+i,v)
  self.u.reg_write(UC_ARM_REG_SP,STACK+0xf0000);self.u.reg_write(UC_ARM_REG_LR,STOP|1)
  try:self.u.emu_start(pc|1,stop,timeout=10000000,count=1000000)
  except Exception as error:raise RuntimeError(f'{self.phase} PC {self.u.reg_read(UC_ARM_REG_PC):#x}, fault={self.fault}, providers={self.providers}, recent={[hex(v) for v in self.recent]}') from error
  assert self.u.reg_read(UC_ARM_REG_PC)==stop,hex(self.u.reg_read(UC_ARM_REG_PC))
  return self.u.reg_read(UC_ARM_REG_R0)
if __name__=='__main__':
 model=Machine();q=model.call(0x7998,phase='chip-info');print(json.dumps(dict(chip=model.read32(0x109b68),chip_info=hex(model.read32(0x120938)))))
 model.payload=DATA+0x10000;model.write32(model.payload,5);model.u.mem_write(model.payload+8,(P.parent/'kernel380/640x480-port8-cores1-config-private.bin').read_bytes());model.write32(DATA,DATA+0xc000)
 q=model.call(0x16534,DATA,phase='config');print(json.dumps(dict(config_ret=q,instructions=model.instructions,providers=model.providers,allocations=model.allocated,config_words=[model.read32(model.config+i) for i in [0,2896,2900,3404]])))
 (P/'fw-config-context-private.bin').write_bytes(model.u.mem_read(DATA,0x20000))
