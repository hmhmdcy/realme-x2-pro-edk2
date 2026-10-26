"""Execute the original downstream AddBLs and accumulator routines offline."""
from pathlib import Path
import importlib.util,json,struct
from unicorn.arm_const import *
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('fw383',HERE.parent/'kernel383/firmware-model.py');f=importlib.util.module_from_spec(s);s.loader.exec_module(f)
rows=[]
for uid in [0,1]:
 m=f.Machine();D=f.DATA;cache=D+0x10000;accum=D+0x12000;heap=D+0x14000;node=D+0x16000;pairs=D+0x18000;commands=D+0x20000;table=0x100cbc
 m.u.mem_write(cache,bytes(2048));m.u.mem_write(accum,bytes(64));m.u.mem_write(heap,bytes(32));m.u.mem_write(node,bytes(16));m.u.mem_write(pairs,bytes(400));m.u.mem_write(commands,bytes(4096))
 m.write32(accum+12,node);m.write32(accum+32,heap);m.write32(node,pairs);m.write32(heap+12,commands);m.write32(heap+16,4096)
 # One external Gamma descriptor, as encoded401. UID=0 deliberately forces
 # programming in AddBLs; UID1 covers the target's ordinary frame/batch value.
 head=D+0x100;link=D+0x200;program=D+0x1000;dmi=D+0x3000
 m.write32(head,link);m.write32(link,program);m.write32(link+4,0)
 m.u.mem_write(program,struct.pack('<8I',0,1,dmi,35<<12,12,uid,0,0));m.u.mem_write(dmi,b''.join(struct.pack('<3I',0x0a0003ff,D+0x4000+1024*i,0x6008|((i+1)<<24)) for i in range(3)))
 sp=f.STACK+0xf0000;m.u.mem_write(sp,struct.pack('<2I',head,7))
 for reg,value in [(UC_ARM_REG_R0,cache),(UC_ARM_REG_R1,table),(UC_ARM_REG_R2,accum),(UC_ARM_REG_R3,0),(UC_ARM_REG_SP,sp),(UC_ARM_REG_LR,f.STOP|1)]:m.u.reg_write(reg,value)
 m.u.emu_start(0x1ed11,f.STOP,timeout=1000000,count=20000);assert m.u.reg_read(UC_ARM_REG_PC)==f.STOP
 m.call(0x1fe54,accum,phase='flush-actual-accumulator')
 count=m.read32(pairs+396);out=[]
 for i in range(count):
  address,size,flag=struct.unpack('<3I',m.u.mem_read(pairs+12+12*i,12));out.append(dict(address=address,bytes=size+1,direct=bool(flag&255),words=list(struct.unpack('<'+'I'*((size+1)//4),m.u.mem_read(address,size+1)))))
 row=dict(uid=uid,original_complete_addbls_executed=True,original_accumulator_functions_executed=True,providers=m.providers,program_pairs=out,lut_bank_registers=[m.read32(table+12*8+i*4) for i in range(2)],cache_bank=m.u.mem_read(cache+1280+12,1)[0],instructions=m.instructions)
 rows.append(row)
(P/'downstream-probe-private.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
