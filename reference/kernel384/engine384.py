"""Extend the immutable 383 preparation fixture to NV21 and padded layouts.

Only the IO configuration differs; all geometry and CDM code remains original.
Stops before hardware enqueue, with no engine or pixel-DMA claim.
"""
from pathlib import Path
import importlib.util,struct
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('fw383',HERE.parent/'kernel383/firmware-model.py');f=importlib.util.module_from_spec(s);s.loader.exec_module(f)

def prepare(blob,width,height,port=8,cores=1,uv_swap=False,stride=None,slice_height=None):
 m=f.Machine();D=f.DATA;m.call(0x7998,phase='original-chip-info')
 stride=width if stride is None else stride;slice_height=height if slice_height is None else slice_height
 m.payload=D+0x10000;wire=bytearray(1216)
 for p in [0,port]:
  off=p*84;struct.pack_into('<III',wire,off,20,width,height);struct.pack_into('<I',wire,off+24,int(uv_swap))
  struct.pack_into('<4I',wire,off+52,stride,slice_height,stride,slice_height//2)
 struct.pack_into('<I',wire,1192,1);m.write32(m.payload,5);m.u.mem_write(m.payload+8,bytes(wire));m.write32(D,D+0xc000)
 m.call(0x16534,D,phase='original-config-io');assert m.read32(m.payload+4)==0 and m.read32(m.config+2900)==48
 frame=bytearray(3816);stripe=D+0x30000;iq=D+0x40000;bl=D+0x60000
 struct.pack_into('<4I',frame,0,stripe,iq,D+0x45000,48);struct.pack_into('<4I',frame,24,bl,0x80000-32,cores,100000000)
 struct.pack_into('<II',frame,84,1,1);struct.pack_into('<II',frame,92,0x20000000,0x20000000+stride*slice_height)
 struct.pack_into('<II',frame,92+port*16,0x24000000,0x24000000+stride*slice_height)
 m.u.mem_write(stripe,blob)
 for off in [52,68,244,260]:m.write32(iq+off,1)
 m.payload=D+0x20000;m.write32(m.payload,6);m.u.mem_write(m.payload+8,bytes(frame))
 m.call(0x17f30,D,phase='original-frame-prepare',stop=0x220a2)
 assert m.read32(m.payload+4)==0
 from unicorn.arm_const import UC_ARM_REG_R1
 return bytes(m.u.mem_read(m.u.reg_read(UC_ARM_REG_R1),32)),bytes(m.u.mem_read(bl,0x80000))
