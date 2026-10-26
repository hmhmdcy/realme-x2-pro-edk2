"""Tie LUT math, actual Gamma module and program descriptors to firmware ABI."""
from pathlib import Path
import importlib.util,json,struct
from unicorn.arm64_const import *
from unicorn.arm_const import UC_ARM_REG_R9,UC_ARM_REG_R5,UC_ARM_REG_PC as FW_PC
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
g=module('gamma401',HERE/'gamma-model.py');f=module('fw383',HERE.parent/'kernel383/firmware-model.py');a=g.Gamma();u=a.u;D=g.DATA
raw=(P.parent/'kernel350/oracle-input-private.bin').read_bytes();expected=(P.parent/'kernel350/oracle-output-private.bin').read_bytes();assert len(raw)//1028==97
actual=b''.join(a.lut(struct.unpack_from('<257f',raw,i)) for i in range(0,len(raw),1028));assert actual==expected
(P/'gamma-lut-oracle-private.bin').write_bytes(actual)
for iova in [0x1000,0x07802b80,0xfffff400]:
 packet=a.headers(iova);assert packet==b''.join(struct.pack('<3I',0x0a0003ff,iova+1024*i,0x6008|((i+1)<<24)) for i in range(3))
assert not a.headers(0x1000,0)
assert set(a.providers)=={'0x4cd8b0','0x4cda68'}
descriptors=[]
for enabled in [0,1]:
 for index in [0,1,2]:
  frame=D+0x50000;node=D+0x60000;iq=D+0x30000;array=D+0x28000;sp=g.h.STACK+0xf0000
  for p,n in [(frame,8192),(node,0x5000),(iq,2584),(array,1024)]:u.mem_write(p,bytes(n))
  u.mem_write(iq+2192,struct.pack('<I',enabled));u.mem_write(node+16072,struct.pack('<I',3));u.mem_write(sp+376,struct.pack('<Q',iq));u.mem_write(sp+368,struct.pack('<Q',frame))
  for r,v in [(UC_ARM64_REG_SP,sp),(UC_ARM64_REG_X26,frame),(UC_ARM64_REG_X19,node),(UC_ARM64_REG_X24,array)]:u.reg_write(r,v)
  u.emu_start(0x2d8160,0x2d8174,count=20);assert a.read32(frame+4136)==20
  for r,v in [(UC_ARM64_REG_X27,node),(UC_ARM64_REG_X28,frame+4120),(UC_ARM64_REG_W8,index),(UC_ARM64_REG_W25,0)]:u.reg_write(r,v)
  u.emu_start(0x2d81e0,0x2d8228,count=100);assert u.reg_read(UC_ARM64_REG_PC)==0x2d8228
  words=struct.unpack('<6I',u.mem_read(frame+4120+index*24+8,24));assert words==(0,35<<12,12 if enabled else 255,0,0,0)
  descriptors.append(dict(enabled=enabled,index=index,program_type=words[2],command_bytes=36,passed=True))
fwrows=[]
for value in [0,1,2,3,0xffffffff]:
 b=f.Machine();v=b.u;v.mem_write(f.DATA,bytes(2584));v.mem_write(f.DATA+2192,struct.pack('<I',value));v.mem_write(f.DATA+0x10000,bytes(64));v.reg_write(UC_ARM_REG_R9,f.DATA);v.reg_write(UC_ARM_REG_R5,f.DATA+0x10000)
 v.emu_start(0x114e5,0x114f4,timeout=1000000,count=20);assert v.reg_read(FW_PC)==0x114f4 and struct.unpack('<2I',v.mem_read(f.DATA+0x10000+24,8))==(0x6060,value&1)
 fwrows.append(dict(iq_value=value,register_value=value&1,passed=True))
report=dict(stage=401,curves=97,lut_compared_bytes=len(actual),different_lut_bytes=0,original_gamma_numeric_fragment_executed=True,original_gamma_module_three_dmi_calls_executed=True,original_complete_write_dmi_and_nested_info_functions_executed=True,only_cmd_storage_and_device_address_materialization_modelled=True,indirect_dmi_opcode=10,inline_opcode76_is_software_command_not_used=True,dmi_register=0x6008,selectors=[1,2,3],channel_bytes=1024,header_bytes=36,iq_enable_offset=2192,enable_register=0x6060,generic_program_type=20,gamma_program_type=12,skip_program_type=255,actual_submit_descriptor_fragment_cases=descriptors,firmware_enable_cases=fwrows,previous_generic_program0_label_withdrawn=True,prior_hardware_observations_not_rewritten=True,phone_changed=False,passed=True)
(HERE/'contract-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
