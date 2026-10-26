"""Run OEM abort entry instructions with synthetic CP15 values and core-save stub."""
from pathlib import Path
import hashlib,json,struct
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_R4,UC_ARM_REG_LR,UC_ARM_REG_PC,UC_ARM_REG_SP
import host
HERE=Path(__file__).resolve().parent;raw=(host.PRIVATE.parent/'kernel352/CAMERA_ICP.elf-private').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='a22bc8adbb4ae97e4f8d728eecb1fd19c1bf866250b0bb7e668951c41c159e63'
phoff=struct.unpack_from('<I',raw,28)[0];stride,count=struct.unpack_from('<HH',raw,42)
segments=[struct.unpack_from('<8I',raw,phoff+i*stride) for i in range(count)]
rows=[]
for kind,start,delta,expected in [('data',0x283cc,8,3),('prefetch',0x283e4,4,1)]:
 for fsr,far,pc in [(0x5,0x0741c000,0x248cc),(0x80d,0x10a00000,0x24a0c)]:
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);maximum=(max(s[2]+s[5] for s in segments if s[0]==1)+4095)&~4095;u.mem_map(0,maximum)
  for typ,offset,va,pa,filesz,memsz,flags,align in segments:
   if typ==1:u.mem_write(va,raw[offset:offset+filesz])
  u.mem_map(0x02000000,0x10000);u.reg_write(UC_ARM_REG_SP,0x0200f000);u.reg_write(UC_ARM_REG_LR,pc+delta)
  for reg in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_R4]:u.reg_write(reg,0x55aa)
  state=dict(cp15_reads=0,core_save_calls=0,handler_argument=None)
  def step(uc,address,size,user):
   if address in [0x283d8,0x283f0]:uc.reg_write(UC_ARM_REG_R4,fsr);state['cp15_reads']+=1;uc.reg_write(UC_ARM_REG_PC,address+4)
   elif address in [0x283dc,0x283f4]:uc.reg_write(UC_ARM_REG_R2,far);state['cp15_reads']+=1;uc.reg_write(UC_ARM_REG_PC,address+4)
   elif address==0x2849c:state['core_save_calls']+=1;uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
   elif address==0x3984:state['handler_argument']=uc.reg_read(UC_ARM_REG_R0);uc.emu_stop()
   elif not (0x283cc<=address<0x28424):raise RuntimeError('Unexpected abort execution '+hex(address))
  u.hook_add(UC_HOOK_CODE,step);u.emu_start(start,0,timeout=1000000,count=1000)
  words=list(struct.unpack('<3I',u.mem_read(0x1099a0,12)))
  assert words==[far,fsr,expected] and state==dict(cp15_reads=2,core_save_calls=1,handler_argument=pc)
  rows.append(dict(path=kind,exception_type=expected,synthetic_fsr=hex(fsr),synthetic_far=hex(far),actual_c_handler_argument=hex(pc),passed=True))
report=dict(stage=370,original_abort_entry_and_common_stores_executed=True,tests=rows,
 fields=[dict(name=n,firmware_offset=hex(a)) for n,a in [('rex_abort_far',0x1099a0),('rex_abort_fsr',0x1099a4),('rex_exception_type',0x1099a8)]],
 data_abort_type=3,prefetch_abort_type=1,abort_argument_is_adjusted_fault_pc=True,
 cp15_fault_registers_synthetic_and_rex_core_save_mocked=True,context_register_layout_not_inferred_from_this_stub=True,
 no_target_exception_decoded=True,phone_operations=False,passed=True)
(HERE/'exception-layout-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
