"""Original firmware preparation, stopping before the hardware enqueue call."""
from pathlib import Path
import hashlib,importlib.util,struct
from unicorn import UC_HOOK_MEM_READ
from unicorn.arm_const import UC_ARM_REG_PC,UC_ARM_REG_R1
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('fm383',HERE/'firmware-model.py');f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
def prepare(blob,width,height,port=8,cores=1,observe=False):
 m=f.Machine();D=f.DATA;m.call(0x7998,phase='original-chip-info')
 m.payload=D+0x10000;wire=bytearray(1216)
 for p in [0,port]:
  off=p*84;struct.pack_into('<III',wire,off,20,width,height);struct.pack_into('<4I',wire,off+52,width,height,width,height//2)
 struct.pack_into('<I',wire,1192,1);m.write32(m.payload,5);m.u.mem_write(m.payload+8,bytes(wire));m.write32(D,D+0xc000)
 m.call(0x16534,D,phase='original-config-io');assert m.read32(m.payload+4)==0 and m.read32(m.config+2900)==48
 frame=bytearray(3816);stripe=D+0x30000;iq=D+0x40000;bl=D+0x60000
 struct.pack_into('<4I',frame,0,stripe,iq,D+0x45000,48);struct.pack_into('<4I',frame,24,bl,0x80000-32,cores,100000000)
 struct.pack_into('<II',frame,84,1,1);struct.pack_into('<II',frame,92,0x20000000,0x20000000+width*height);struct.pack_into('<II',frame,92+port*16,0x24000000,0x24000000+width*height)
 m.u.mem_write(stripe,blob)
 for off in [52,68,244,260]:m.write32(iq+off,1)
 m.payload=D+0x20000;m.write32(m.payload,6);m.u.mem_write(m.payload+8,bytes(frame));reads={}
 if observe:
  def reading(u,access,address,size,value,user):
   for off in range(max(address,stripe)-stripe,min(address+size,stripe+len(blob))-stripe):reads.setdefault(off,set()).add(u.reg_read(UC_ARM_REG_PC))
  m.u.hook_add(UC_HOOK_MEM_READ,reading,begin=stripe,end=stripe+len(blob)-1)
 m.call(0x17f30,D,phase='original-frame-prepare',stop=0x220a2)
 assert m.read32(m.payload+4)==0
 job=bytes(m.u.mem_read(m.u.reg_read(UC_ARM_REG_R1),32));commands=bytes(m.u.mem_read(bl,0x80000))
 return m,job,commands,reads
