"""Execute OEM IFE-parent LTM exposure-history binding without replacing it."""
from pathlib import Path
import importlib.util,json,struct
from unicorn.arm64_const import *
HERE=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel424')
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
module('storage284',HERE.parent/'kernel284/storage.py').mounted_build();h=module('hal380',HERE.parent/'kernel380/hal-machine.py');m=h.Machine();u=m.u
obj,inp,config=[h.DATA+n for n in [0x10000,0x20000,0x30000]]
rows=[]
for frame,bet,oldLux,newLux in [(9,0,10,30),(9,0,30,10),(9,0,30,30),(1,0,10,30),(3,0,10,30),(4,0,10,30),(4,1,10,30),(5,1,10,30)]:
 u.mem_write(obj,bytes([0xa7])*1024);u.mem_write(inp,bytes(20000));u.mem_write(config,bytes(128))
 u.mem_write(obj+136,struct.pack('<4f',oldLux,oldLux,-111,1))
 u.mem_write(inp+2776,struct.pack('<Q',frame));u.mem_write(inp+2892,struct.pack('<f',newLux))
 for at,value in [(2884,1),(2912,1),(2880,1),(2872,1)]:u.mem_write(inp+at,struct.pack('<f',value))
 u.mem_write(inp+19632,struct.pack('<Q',0x10000));u.mem_write(config+16,struct.pack('<I',bet));u.mem_write(config+52,struct.pack('<I',2))
 for reg,value in [(UC_ARM64_REG_X26,obj),(UC_ARM64_REG_X24,inp),(UC_ARM64_REG_X28,config)]:u.reg_write(reg,value)
 u.emu_start(0x35fe8c,0x35ffbc,count=300);assert u.reg_read(UC_ARM64_REG_PC)==0x35ffbc
 current,previous=struct.unpack('<2f',u.mem_read(obj+140,8));reset=frame<=(4 if bet else 3)
 assert current==newLux and previous==(newLux if reset else oldLux),(frame,bet,current,previous)
 rows.append(dict(frame=frame,register_bet=bool(bet),new_lux=newLux,old_lux=oldLux,current=current,previous=previous,warmup_reset=reset))
r=dict(stage=424,native_range=['0x35fe8c','0x35ffbc'],cases=len(rows),ife_parent_id='0x10000',
 current_ltm_exposure_history_uses_request_lux_offset2892=True,physical_exposure_product_not_this_input=True,
 first_requests_reset_previous_to_current=True,native_instructions=m.instructions,providers=m.providers,rows=rows,
 native_policy_warmup_distinguished_from_current_native_candidate_commit_policy=True,phone_accessed=False,passed=True)
(HERE/'exposure-domain-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
