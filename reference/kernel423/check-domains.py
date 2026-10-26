"""Execute native IFE publication and IPE LTM Gamma transport fragments."""
from pathlib import Path
import importlib.util,json,struct
from unicorn.arm64_const import *
HERE=Path(__file__).resolve().parent
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
module('storage284',HERE.parent/'kernel284/storage.py').mounted_build()
h=module('hal380',HERE.parent/'kernel380/hal-machine.py');m=h.Machine();u=m.u
obj,inp,calc,src=[h.DATA+n for n in [0x10000,0x20000,0x30000,0x40000]]
green=[(i*13)%1024 for i in range(64)]
for fill in [0,0xa5]:
 for delta in [0,511]:
  u.mem_write(calc,bytes([fill])*9000);u.mem_write(obj+128,struct.pack('<Q',src));u.mem_write(inp+2528,struct.pack('<Q',calc))
  u.mem_write(src,struct.pack('<64I',*[v|(delta<<10) for v in green]))
  for reg,value in [(UC_ARM64_REG_X20,obj),(UC_ARM64_REG_X19,inp)]:u.reg_write(reg,value)
  u.emu_start(0x31f384,0x31f5b0,count=500)
  assert u.reg_read(UC_ARM64_REG_PC)==0x31f5b0
  assert bytes(u.mem_read(calc+7544,256))==struct.pack('<64I',*green)
  assert bytes(u.mem_read(calc+7544+256,4))==bytes([fill])*4 and m.read32(calc+7540)==1
  # This is an intentional explicit candidate endpoint, not a recovered
  # Android metadata endpoint: the native publisher above leaves it untouched.
  endpoint=1024;u.mem_write(calc+7544+256,struct.pack('<I',endpoint))
  sp=h.STACK+0xe0000;u.mem_write(obj,bytes([0xa7])*1024);u.mem_write(sp+168,struct.pack('<Q',obj+264))
  for reg,value in [(UC_ARM64_REG_X1,calc+7544),(UC_ARM64_REG_X26,obj),(UC_ARM64_REG_SP,sp)]:u.reg_write(reg,value)
  u.emu_start(0x35ffbc,0x36005c,count=100)
  assert u.reg_read(UC_ARM64_REG_PC)==0x36005c
  assert bytes(u.mem_read(obj+168,260))==struct.pack('<65f',*green,endpoint)
  assert bytes(u.mem_read(obj+428,16))==bytes([0xa7])*16
r=dict(stage=423,native_ife_publication_cases=4,native_ltm_transport_cases=4,
 native_ife_publishes_64_low10bit_green_bases=True,native_ife_does_not_publish_node64=True,
 ltm_reads_65_unsigned_nodes_converted_to_float=True,changing_dmi_delta_does_not_supply_metadata_endpoint=True,
 candidate_endpoint_is_explicit_hardware_segment_reconstruction=True,android_metadata_endpoint_not_claimed=True,
 native_instructions=m.instructions,providers=m.providers,phone_accessed=False,passed=True)
(HERE/'domains-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
