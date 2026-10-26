"""Check the original ICP Thumb queue-header lookup in isolation."""
from pathlib import Path
import itertools,json,struct
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_HOOK_CODE,UC_HOOK_INTR
from unicorn.arm_const import *
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
TABLE=0x1000000;STACK=0x2000000;STOP=0x4000000;REG=0xe0010000;OUT=TABLE+0xf000
raw=(P/'CAMERA_ICP.elf-private').read_bytes();assert raw[:7]==b'\x7fELF\x01\x01\x01'
phoff=struct.unpack_from('<I',raw,28)[0];stride,count=struct.unpack_from('<HH',raw,42)
segments=[struct.unpack_from('<8I',raw,phoff+i*stride) for i in range(count)]
assert struct.unpack_from('<H',raw,18)[0]==40
u=Uc(UC_ARCH_ARM,UC_MODE_THUMB);maximum=max(s[2]+s[5] for s in segments if s[0]==1);maximum=(maximum+4095)&~4095;u.mem_map(0,maximum)
for kind,offset,va,pa,filesz,memsz,flags,align in segments:
 if kind==1:u.mem_write(va,raw[offset:offset+filesz])
for address,size in [(TABLE,0x10000),(STACK,0x10000),(STOP,0x1000),(REG,0x1000)]:u.mem_map(address,size)
u.mem_write(REG+0x58,struct.pack('<I',TABLE));instructions=0;mapping_calls=[];assert_calls=0
def step(uc,pc,size,user):
 global instructions,assert_calls
 instructions+=1
 if pc==0x107ca:
  address=uc.reg_read(UC_ARM_REG_R1);length=uc.reg_read(UC_ARM_REG_R2)
  assert address==TABLE or address in [0x6000000,0x6200000,0x6400000]
  assert length in [4096,65536,1048576]
  mapping_calls.append(dict(address=address,size=length));uc.reg_write(UC_ARM_REG_R0,0);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
 if pc==0x246fa:
  assert uc.reg_read(UC_ARM_REG_R0)==1,'Original firmware assertion condition failed'
  assert_calls+=1;uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
 if not 0x1a970<=pc<0x1aa10:raise RuntimeError('Unexpected firmware path: '+hex(pc))
def interrupt(uc,number,user):raise RuntimeError('Firmware interrupt/system call rejected: '+str(number))
u.hook_add(UC_HOOK_CODE,step);u.hook_add(UC_HOOK_INTR,interrupt)
records=[]
for order in itertools.permutations(range(3)):
 u.mem_write(TABLE,b'\0'*4096);u.mem_write(TABLE,struct.pack('<6I',0xffffffff,2892,24,956,3,3))
 for index,kind in enumerate(order):
  base=TABLE+24+index*956
  for offset,value in [(60,1),(124,0x6000000+kind*0x200000),(188,kind),(252,[1024,1025,16385][kind])]:u.mem_write(base+offset,struct.pack('<I',value))
 for kind in [0,1,2,3,255]:
  before=len(mapping_calls);u.mem_write(OUT,struct.pack('<I',0xdeadbeef));u.reg_write(UC_ARM_REG_SP,STACK+0xf000);u.reg_write(UC_ARM_REG_LR,STOP|1)
  u.reg_write(UC_ARM_REG_R0,kind);u.reg_write(UC_ARM_REG_R1,OUT);u.emu_start(0x1a971,STOP,timeout=100000,count=1000)
  assert u.reg_read(UC_ARM_REG_PC)==STOP;status=u.reg_read(UC_ARM_REG_R0);pointer=struct.unpack('<I',u.mem_read(OUT,4))[0]
  assert status==(0 if kind<3 else 1)
  assert pointer==(TABLE+24+order.index(kind)*956 if kind<3 else 0xdeadbeef)
  calls=mapping_calls[before:];assert len(calls)==(2 if kind<3 else 1)
  if kind<3:assert calls[-1]['size']==[4096,65536,1048576][kind]
  records.append(dict(order=list(order),queue_id=kind,status=status,header_offset=pointer-TABLE if kind<3 else None,map_sizes=[c['size'] for c in calls]))
(P/'firmware-queue-cases-private.json').write_text(json.dumps(records,indent=2)+'\n')
report=dict(stage=352,original_firmware_function='HFI_QueueGetQHdr',thumb_function=['0x1a971','0x1aa10'],
 calls=len(records),instructions=instructions,queue_header_bytes=956,queue_table_header_bytes=24,
 queue_header_first_field_offset=60,queue_type_offset=188,queue_start_addr_offset=124,queue_size_offset=252,
 queue_lookup_uses_type_id_and_fixed_stride=True,queue_size_consumed_as_words=True,
 all_queue_permutations_and_unknown_ids_verified=True,io_register_qtable_pointer_address=hex(REG+0x58),
 actual_memory_mapping_not_exercised=True,memory_mapping_stub_calls=len(mapping_calls),successful_assertion_stub_calls=assert_calls,
 function_only_no_firmware_boot=True,no_phone_operations=True,passed=True)
(HERE/'firmware-queue-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
