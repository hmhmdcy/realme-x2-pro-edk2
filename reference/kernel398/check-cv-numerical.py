"""Execute the target's inlined CV OEM calculation without replacing arithmetic."""
from pathlib import Path
import importlib.util,json,math,random,struct
from unicorn.arm64_const import *
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('hal380',HERE.parent/'kernel380/hal-machine.py');h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
a=h.Machine();u=a.u;D=h.DATA
f32=lambda x:struct.unpack('<f',struct.pack('<f',x))[0]
roundaway=lambda x:math.floor(x+.5) if x>=0 else math.ceil(x-.5)
clamp=lambda x,lo,hi:min(max(x,lo),hi)
cases=[];scaled=[0,1,2,4,5,6,7,8,9,10,11]
for index in range(14):
 for n in [-4096,-2048,-1024,-1.5,-.5,0,.5,1.5,1023,2047,4095]:
  v=[0.]*14;v[index]=n/256 if index in scaled else n;cases.append(v)
rng=random.Random(398)
for _ in range(128):cases.append([rng.randrange(-8192,8192)/256 if i in scaled else rng.randrange(-4096,4096)/2 for i in range(14)])
actual=[]
for values in cases:
 obj=D+0xc000;data=D+0xd000;override=D+0x1000
 for p,n in [(obj,1024),(data,4096),(override,0x3000)]:u.mem_write(p,bytes(n))
 u.mem_write(data+2792,struct.pack('<Q',override));u.mem_write(override+8864,struct.pack('<14f',*values));u.mem_write(override+8924,struct.pack('<I',1))
 u.reg_write(UC_ARM64_REG_X19,obj);u.reg_write(UC_ARM64_REG_X20,data);u.reg_write(UC_ARM64_REG_SP,h.STACK+0xf0000)
 u.emu_start(0x34c374,0x34c59c,timeout=1000000,count=1000);assert u.reg_read(UC_ARM64_REG_PC)==0x34c59c
 q=[clamp(roundaway(f32(f32(v)*(256 if i in scaled else 1))),-2048 if i in scaled else -1024,2047 if i in scaled else 1023) for i,v in enumerate(values)]
 words=[(q[0]&0xfff)|((q[1]&0xfff)<<16),(q[2]&0xfff)|((q[3]&0x7ff)<<16)]
 words.extend([(q[i]&0xfff)|((q[i+1]&0xfff)<<16) for i in [4,6,8,10]])
 # The actual binary leaf stores kcr then kcb; the packet writes cb then cr.
 words.extend([q[13]&0x1fff,q[12]&0x1fff])
 registers=bytes(u.mem_read(obj+112,32));assert registers==struct.pack('<8I',*words)
 assert not any(bytes(u.mem_read(obj+144,32)))
 actual.append(registers)
(P/'cv-synthetic-registers-private.bin').write_bytes(b''.join(actual))
assert not a.providers
report=dict(stage=398,cases=len(cases),compared_bytes=len(cases)*32,different_bytes=0,target_original_inlined_oem_numerical_fragment_executed=True,fragment=['0x34c374','0x34c59c'],no_arithmetic_or_register_stub=True,complete_execute_or_factory_interpolation_not_claimed=True,coefficient_q_fraction=8,coefficient_signed_bits=12,y_offset_clamp_signed_bits=11,kcb_kcr_numerical_clamp_signed_bits=11,kcb_kcr_register_fields_bits=13,leaf_chroma_fields='am ap bm bp cm cp dm dp kcr kcb after r_to_y g_to_y b_to_y y_offset',newer_reference_source_not_used_as_target_numeric_authority=True,hardware_colour_domain_established=False,phone_changed=False,passed=True)
(HERE/'cv-numerical-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
