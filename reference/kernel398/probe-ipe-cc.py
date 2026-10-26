"""Resolve the actual IPE caller type before choosing a numerical oracle."""
from pathlib import Path
import importlib.util,json,struct
from unicorn.arm64_const import *
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('colour396',HERE.parent/'kernel396/colour-model.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
a=m.Colour();u=a.u
assert struct.unpack('<4I',u.mem_read(0xcef20,16))==(2,0,0,0)
# Execute the actual output-initialization instructions, bounded before unrelated
# module work. No instruction or constant in this fragment is replaced.
u.reg_write(UC_ARM64_REG_SP,m.h.STACK+0xf0000)
u.emu_start(0x350e40,0x350e60,count=32)
actual=bytes(u.mem_read(m.h.STACK+0xf0010,16));assert struct.unpack('<4I',actual)==(2,0,0,0)
def calculate(matrix,offsets,shift):
 inp=m.DATA;override=inp+0x1000;out=inp+0x5000;regs=inp+0x6000
 u.mem_write(inp,bytes(256));u.mem_write(override,bytes(0x3000));u.mem_write(regs,bytes(64))
 u.mem_write(override+5676,struct.pack('<12f',*matrix,*offsets))
 u.mem_write(override+5732,struct.pack('<I',shift));u.mem_write(override+5728,struct.pack('<I',1))
 u.mem_write(out,struct.pack('<IIQ',2,0,regs))
 assert a.call(0x37f070,inp,override,out,phase='actual-ipe-type2-cc')==0
 assert bytes(u.mem_read(regs+36,28))==bytes(28)
 return bytes(u.mem_read(regs,36))
differences=[];old=m.Colour()
for offset in [-4096,-1025,-1024,-1,0,1,1023,1024,4095]:
 mat=[1.,0,0,0,1.,0,0,0,1.];ofs=[offset]*3
 right=calculate(mat,ofs,0);wrong=old.calculate(mat,ofs,0)
 differences.append(dict(offset=offset,different=right!=wrong))
(P/'caller-output-private.bin').write_bytes(actual)
report=dict(stage=398,actual_ipe_cc_output_type=2,caller_initialization_executed=True,actual_ipe_oem_region_offset=5676,actual_ipe_oem_enable_offset=5728,actual_ipe_oem_qshift_offset=5732,previous396_oracle_output_type=1,previous396_oracle_ipe_scope_withdrawn=True,previous397_zero_offset_diagonal_pixel_observations_retained=True,offset_differential_cases=differences,phone_changed=False,passed=True)
(HERE/'caller-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
