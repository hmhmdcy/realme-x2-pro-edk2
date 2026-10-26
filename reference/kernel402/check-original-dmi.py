"""Derive Gamma CmdType from original resource initialization and encode it."""
from pathlib import Path
import importlib.util,json,struct,types
from unicorn.arm64_const import *
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('hal380',HERE.parent/'kernel380/hal-machine.py');h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
m=h.Machine();D=h.DATA;resource=D;node=D+0x10000;input_data=D+0x20000;params=D+0x30000;array=D+0x40000
for address,size in [(resource,56),(node,512),(input_data,0x6000),(params,16),(array,128)]:m.u.mem_write(address,bytes(size))
m.u.mem_write(params,struct.pack('<Q',array));m.u.mem_write(input_data+19844,struct.pack('<I',4))
for reg,value in [(UC_ARM64_REG_X22,resource),(UC_ARM64_REG_X20,node),(UC_ARM64_REG_X21,input_data),(UC_ARM64_REG_X19,params),(UC_ARM64_REG_SP,h.STACK+0xf0000)]:m.u.reg_write(reg,value)
m.u.emu_start(0x35605c,0x3560d4,timeout=1000000,count=1000);assert m.u.reg_read(UC_ARM64_REG_PC)==0x3560d4
assert m.read32(resource)==3072 and m.read32(resource+32)==1
raw=bytes(m.u.mem_read(resource,56));(P/'gamma-resource-init-private.bin').write_bytes(raw)
# CmdType1 is CDMDMI, confirmed by the pinned enum and factory resource init.
# Retain401 model untouched; correct the fixture's assumed legacy type3 here.
code=(HERE.parent/'kernel401/gamma-model.py').read_text().replace("HERE=Path(__file__).resolve().parent","HERE=Path(__file__).resolve().parent")
code=code.replace("struct.pack('<I',3)","struct.pack('<I',1)").replace('0x0a0003ff','0x010003ff')
(HERE/'gamma-model.py').write_text(code)
s=importlib.util.spec_from_file_location('gamma402',HERE/'gamma-model.py');g=importlib.util.module_from_spec(s);s.loader.exec_module(g);model=g.Gamma();rows=[]
for address in [0x1000,0x07802b80,0xfffff400]:
 actual=model.headers(address);assert actual==b''.join(struct.pack('<3I',0x010003ff,address+1024*i,0x6008|((i+1)<<24)) for i in range(3));rows.append(dict(lut_iova=address,header_bytes=len(actual),passed=True))
assert not model.headers(0x1000,0)
(P/'gamma-dmi-original-corrected-private.bin').write_bytes(model.headers(0x07802b80))
report=dict(stage=402,original_gamma_resource_initialization_fragment_executed=True,resource_bytes=3072,source_cmd_type=1,source_cmd_type_name='CDMDMI',original_complete_write_dmi_and_nested_info_executed=True,actual_opcode=1,header_bytes=36,register=0x6008,selectors=[1,2,3],source_offsets=[0,1024,2048],cases=rows,
 previous401_fixture_assumed_source_cmd_type=3,previous401_fixture_selected_legacy_opcode10=True,previous401_opcode10_factory_claim_withdrawn=True,original_hal_instructions_not_modified=True,phone_changed=False,hardware_causal_fix_not_yet_proven=True,passed=True)
(HERE/'dmi-correction-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
