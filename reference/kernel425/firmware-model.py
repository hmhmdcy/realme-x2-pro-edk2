"""Complete retained firmware config/frame preparation for explicit multipass IO."""
from pathlib import Path
import importlib.util,struct
from unicorn.arm_const import UC_ARM_REG_R1
HERE=Path(__file__).resolve().parent
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
r=module('routing396',HERE.parent/'kernel396/probe-routing.py');f=r.f
def prepare(config,stripe,iq_blob,width,height,pd10_bytes,pd10_iova=0x20800000):
 m=r.Firmware();D=f.DATA;m.call(0x7998,phase='chip-info')
 m.payload=D+0x10000;m.write32(m.payload,5);m.u.mem_write(m.payload+8,config);m.write32(D,D+0xc000)
 assert m.call(0x16534,D,phase='multipass-config')==0 and m.read32(m.payload+4)==0
 scratch=m.read32(m.config+2900);configured_passes=m.read32(m.config+2896)
 assert 0<scratch<=0x40000 and configured_passes==2
 stripe_addr=D+0x30000;iq_addr=D+0x40000;scratch_addr=D+0x80000;bl=D+0x100000;arrays=iq_addr+2592
 frame=bytearray(3816);struct.pack_into('<4I',frame,0,stripe_addr,iq_addr,scratch_addr,scratch)
 struct.pack_into('<4I',frame,24,bl,0x80000-32,2,100000000);struct.pack_into('<I',frame,48,32)
 struct.pack_into('<II',frame,84,1,1)
 struct.pack_into('<II',frame,92,0x20000000,0x20000000+width*height)
 struct.pack_into('<I',frame,108,pd10_iova)
 struct.pack_into('<II',frame,92+8*16,0x24000000,0x24000000+width*height)
 m.u.mem_write(stripe_addr,stripe);m.u.mem_write(iq_addr,iq_blob)
 m.u.mem_write(scratch_addr,bytes([0xa7])*scratch);m.u.mem_write(bl,bytes([0xa5])*0x80000)
 m.payload=D+0x20000;m.write32(m.payload,6);m.u.mem_write(m.payload+8,bytes(frame))
 for off in range(44,84,4):m.write32(m.payload+8+off,arrays+(32 if off==44 else 96 if off==48 else 0))
 m.call(0x17f30,D,phase='multipass-complete-frame-preparation',stop=0x220a2)
 assert m.read32(m.payload+4)==0
 job=bytes(m.u.mem_read(m.u.reg_read(UC_ARM_REG_R1),32));commands=bytes(m.u.mem_read(bl,0x80000))
 return m,job,commands,dict(required_scratch_bytes=scratch,configured_passes=configured_passes,pd10_address=pd10_iova,pd10_bytes=pd10_bytes,frame=bytes(frame))
