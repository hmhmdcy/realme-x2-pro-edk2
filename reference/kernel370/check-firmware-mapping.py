"""Execute retained static page-table setup and request wait instructions offline."""
from pathlib import Path
import hashlib,json,struct
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R4,UC_ARM_REG_LR,UC_ARM_REG_PC,UC_ARM_REG_SP
import host
HERE=Path(__file__).resolve().parent
raw=(host.PRIVATE.parent/'kernel352/CAMERA_ICP.elf-private').read_bytes()
digest=hashlib.sha256(raw).hexdigest()
assert digest=='a22bc8adbb4ae97e4f8d728eecb1fd19c1bf866250b0bb7e668951c41c159e63'
phoff=struct.unpack_from('<I',raw,28)[0];stride,count=struct.unpack_from('<HH',raw,42)
segments=[struct.unpack_from('<8I',raw,phoff+i*stride) for i in range(count)]
STACK=0x02000000;STOP=0x04000000;REG=0xe0010000;L1=0x340000
def machine():
 u=Uc(UC_ARCH_ARM,UC_MODE_THUMB)
 maximum=(max(s[2]+s[5] for s in segments if s[0]==1)+4095)&~4095
 u.mem_map(0,maximum)
 for kind,offset,va,pa,filesz,memsz,flags,align in segments:
  if kind==1:u.mem_write(va,raw[offset:offset+filesz])
 for address,size in [(STACK,0x10000),(STOP,4096)]:u.mem_map(address,size)
 u.reg_write(UC_ARM_REG_SP,STACK+0xf000);u.reg_write(UC_ARM_REG_LR,STOP|1)
 return u
u=machine();static_records=[]
for i in range(4):
 words=struct.unpack('<8I',u.mem_read(0x28fa4+32*i,32))
 static_records.append(list(words))
(host.PRIVATE/'static-map-records-private.json').write_text(json.dumps(static_records)+'\n')
calls=[]
def static_step(uc,pc,size,user):
 if 0x4274<=pc<0x4326:return
 if pc!=0x25ef4:raise RuntimeError('Unexpected static-map provider '+hex(pc))
 r0=uc.reg_read(UC_ARM_REG_R0);r1=uc.reg_read(UC_ARM_REG_R1);r2=uc.reg_read(UC_ARM_REG_R2)
 assert r0==L1 and r1==0 and r2==0x4000
 uc.mem_write(r0,bytes(r2));calls.append('memset-L1');uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
u.hook_add(UC_HOOK_CODE,static_step);u.emu_start(0x42d9,STOP,timeout=1000000,count=100000)
assert u.reg_read(UC_ARM_REG_PC)==STOP and calls==['memset-L1']
page_table=bytes(u.mem_read(L1,16384));(host.PRIVATE/'static-L1-private.bin').write_bytes(page_table)
entries=struct.unpack('<4096I',page_table)
walk=[]
for address in [0,0x1099a0,0x340000,0x07400000,0x0741c000,0x10a00000,0xe001004c,0xe0044080]:
 pte=entries[address>>20];is_section=(pte&3)==2
 output=(pte&0xfff00000)|(address&0xfffff) if is_section else None
 walk.append(dict(firmware_va=hex(address),l1_pte=hex(pte),section=is_section,output_iova=None if output is None else hex(output)))
assert all(w['section'] and w['output_iova']==w['firmware_va'] for w in walk if int(w['firmware_va'],16)<0x500000 or int(w['firmware_va'],16)>=0xe0000000)
assert all(not w['section'] for w in walk if 0x07400000<=int(w['firmware_va'],16)<=0x10a00000)
# The entry's busy wait must not consume later CSR fields before request=1.
# Execute the real wait block only; no RTOS, CP15 or dynamic VMM is simulated.
wait_rows=[]
for initial,release_after in [(1,None),(0,5),(2,7),(0,None)]:
 u=machine();u.mem_map(REG,4096);u.mem_write(REG+0x48,struct.pack('<I',initial))
 u.reg_write(UC_ARM_REG_R0,0)
 u.reg_write(UC_ARM_REG_R4,REG+0x44)
 state=dict(reads=0,version_stores=[],released=False)
 def wait_step(uc,pc,size,user):
  if pc==0x24806:
   state['reads']+=1
   if release_after and state['reads']==release_after:uc.mem_write(REG+0x48,struct.pack('<I',1));state['released']=True
  if pc==0x7e1c:
   assert uc.reg_read(UC_ARM_REG_R0)==REG+0x44
   uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  elif not (0x24806<=pc<0x24824):raise RuntimeError('Unexpected wait execution '+hex(pc))
 def store(uc,access,address,size,value,user):
  if address==REG+0x44:state['version_stores'].append(value)
 u.hook_add(UC_HOOK_CODE,wait_step);u.hook_add(UC_HOOK_MEM_WRITE,store)
 u.emu_start(0x24807,0x24824,timeout=1000000,count=300)
 ready=initial==1 or release_after is not None
 assert state['version_stores']==([0x01000100] if ready else [])
 assert (u.reg_read(UC_ARM_REG_PC)==0x24824)==ready
 wait_rows.append(dict(initial_request=initial,release_on_read=release_after,request_reads=state['reads'],version_written=ready,passed=True))
report=dict(stage=370,firmware_sha256=digest,static_map_actual_functions=['vmm_preinit','program_section_entries'],
 static_table_record_slots=len(static_records),page_table_sha256=hashlib.sha256(page_table).hexdigest(),walk=walk,wait_tests=wait_rows,
 actual_version_write_follows_request_one=True,shared_heap_and_sfr_need_later_dynamic_mapping=True,
 only_L1_memset_mocked_in_static_map_test=True,cp15_cache_scheduler_dynamic_vmm_not_executed=True,
 physical_smmu_mapping_and_target_exception_not_proven=True,phone_operations=False,passed=True)
(HERE/'firmware-mapping-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='static_table_records'},indent=2))
