"""Execute complete OEM abort/context-save instructions with synthetic CP15 only."""
from pathlib import Path
import hashlib,json,struct
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_R4,UC_ARM_REG_LR,UC_ARM_REG_PC,UC_ARM_REG_SP,UC_ARM_REG_CPSR,UC_ARM_REG_SPSR
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
raw=(P.parent/'kernel352/CAMERA_ICP.elf-private').read_bytes();assert hashlib.sha256(raw).hexdigest()=='a22bc8adbb4ae97e4f8d728eecb1fd19c1bf866250b0bb7e668951c41c159e63'
phoff=struct.unpack_from('<I',raw,28)[0];stride,count=struct.unpack_from('<HH',raw,42);segments=[struct.unpack_from('<8I',raw,phoff+i*stride) for i in range(count)]
rows=[]
for kind,start,delta,expected in [('data',0x283cc,8,3),('prefetch',0x283e4,4,1)]:
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);maximum=(max(s[2]+s[5] for s in segments if s[0]==1)+4095)&~4095;u.mem_map(0,maximum)
 for typ,offset,va,pa,filesz,memsz,flags,align in segments:
  if typ==1:u.mem_write(va,raw[offset:offset+filesz])
 # Use the original cold-start stack tops in their actual banked modes.
 for mode,sp in [(0xd3,0x103690),(0xd7,0x103794),(0xdb,0x1049a0),(0xd2,0x104798),(0xd1,0x10489c),(0xdf,0x1089a4)]:
  u.reg_write(UC_ARM_REG_CPSR,mode);u.reg_write(UC_ARM_REG_SP,sp)
 u.reg_write(UC_ARM_REG_CPSR,0xd7);u.reg_write(UC_ARM_REG_SPSR,0x3f)
 fault_pc=0x24a0c;u.reg_write(UC_ARM_REG_LR,fault_pc+delta)
 for reg in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_R4]:u.reg_write(reg,0x55aa)
 state=dict(cp15_reads=0,handler_argument=None)
 def step(uc,address,size,user):
  if address in [0x283d8,0x283f0]:uc.reg_write(UC_ARM_REG_R4,0x805);state['cp15_reads']+=1;uc.reg_write(UC_ARM_REG_PC,address+4)
  elif address in [0x283dc,0x283f4]:uc.reg_write(UC_ARM_REG_R2,0x10a00000);state['cp15_reads']+=1;uc.reg_write(UC_ARM_REG_PC,address+4)
  elif address==0x3984:state['handler_argument']=uc.reg_read(UC_ARM_REG_R0);uc.emu_stop()
  elif not (0x283cc<=address<0x28424 or 0x2849c<=address<0x285d4):raise RuntimeError('Unexpected abort execution '+hex(address))
 u.hook_add(UC_HOOK_CODE,step);u.emu_start(start,0,timeout=1000000,count=3000)
 assert state==dict(cp15_reads=2,handler_argument=fault_pc)
 assert struct.unpack('<3I',u.mem_read(0x1099a0,12))==(0x10a00000,0x805,expected)
 context_address=struct.unpack('<I',u.mem_read(0x100098,4))[0];assert context_address==0x108bc4
 context=bytes(u.mem_read(context_address,160));abt_sp=struct.unpack_from('<I',context,0x58)[0]
 assert abt_sp==0x103794-36 and struct.unpack('<I',u.mem_read(abt_sp+32,4))[0]==fault_pc
 assert bytes(u.mem_read(0x1099ac,256))==bytes(256),'A5ContextRegisters was not this exception save destination'
 (P/('synthetic-'+kind+'-context-private.bin')).write_bytes(context)
 ranges=[(0x1099a0,3),(0x100098,1),(0x108bc4,40),(0x103714,32)]
 values={str(address+4*i):struct.unpack('<I',u.mem_read(address+4*i,4))[0] for address,n in ranges for i in range(n)}
 (P/('synthetic-'+kind+'-snapshot-private.json')).write_text(json.dumps(values)+'\n')
 rows.append(dict(path=kind,context_save_function_executed=True,abt_sp_context_offset='0x58',fault_pc_at_saved_abt_sp_plus=32,
  original_abt_stack_top='0x103794',passed=True))
profile=dict(stage=372,firmware_sha256=hashlib.sha256(raw).hexdigest(),windows=[dict(offset=0x1099a0,words=3,role='exception-globals'),dict(offset=0x100098,words=1,role='architecture-context-pointer'),dict(offset=0x108bc4,words=40,role='original-context-destination'),dict(offset=0x103714,words=32,role='original-abort-stack-tail')],
 original_context_save_executed=True,cp15_values_synthetic=True,rtos_cache_and_hardware_mmu_not_simulated=True,
 field_layout=dict(far=0x1099a0,fsr=0x1099a4,type=0x1099a8,context_pointer=0x100098,initial_context=0x108bc4,abt_sp_offset=0x58,fault_pc_stack_offset=32),
 A5ContextRegisters_not_the_executed_abort_save_destination=True,tests=rows,phone_operations=False,passed=True)
(HERE/'firmware-context-validation.json').write_text(json.dumps(profile,indent=2)+'\n');print(json.dumps(profile,indent=2))
