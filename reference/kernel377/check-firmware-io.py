"""Execute original async dispatch/map/unmap and IO callback with bounded mocks."""
from pathlib import Path
import hashlib,json,struct
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_HOOK_CODE
from unicorn.arm_const import *
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;raw=(P.parent/'kernel352/CAMERA_ICP.elf-private').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='a22bc8adbb4ae97e4f8d728eecb1fd19c1bf866250b0bb7e668951c41c159e63'
phoff=struct.unpack_from('<I',raw,28)[0];stride,count=struct.unpack_from('<HH',raw,42);segments=[struct.unpack_from('<8I',raw,phoff+i*stride) for i in range(count)]
STACK=0x2000000;STOP=0x4000000;HEAP=0x5000000;DATA=0x6000000;PAYLOAD=DATA+0x4000;LIST=DATA+0x1000;INFO=DATA+0x1200;NODE=INFO+12;VMM=DATA+0x1300
tokens=(0x1122334455667788,0x99aabbccddeeff00);rows=[]
def machine():
 u=Uc(UC_ARCH_ARM,UC_MODE_THUMB);maximum=(max(s[2]+s[5] for s in segments if s[0]==1)+4095)&~4095;u.mem_map(0,maximum)
 for kind,offset,va,pa,filesz,memsz,flags,align in segments:
  if kind==1:u.mem_write(va,raw[offset:offset+filesz])
 for address,size in [(STACK,0x10000),(STOP,4096),(HEAP,0x10000),(DATA,0x10000)]:u.mem_map(address,size)
 return u
for operation in ['map','unmap','config']:
 u=machine();state=dict(alloc=0,packets=[],queued=[],maps=[],freed=[],copies=[])
 u.mem_write(0x109b80,struct.pack('<I',LIST))
 if operation=='unmap':
  u.mem_write(LIST,struct.pack('<II',NODE,NODE));u.mem_write(INFO,struct.pack('<6I',0x07420000,4096,VMM,INFO,0,0));u.mem_write(VMM,struct.pack('<I',0x12345678))
 if operation in ['map','unmap']:
  opcode=14 if operation=='map' else 15;packet=struct.pack('<IIIQQIIQIII',56,0x101000a,opcode,*tokens,1,0x12345678,0,1,0x07420000,4096)
 else:
  opcode=5;packet=struct.pack('<IIIQQIII',40,0x101000e,5,*tokens,1,0x12345678,PAYLOAD)
  payload=bytearray(1216);struct.pack_into('<I',payload,1192,1);struct.pack_into('<Q',payload,1208,0x13579bdf2468ace0);u.mem_write(PAYLOAD,bytes(payload))
 u.mem_write(DATA,packet)
 def step(uc,pc,size,user):
  if 0x1c854<=pc<0x1e8cc or 0x1e8cc<=pc<0x1e950 or 0x1e950<=pc<0x1e9d2 or 0x1eace<=pc<0x1eaf2 or 0x1ec0c<=pc<0x1ecd6:return
  a=uc.reg_read(UC_ARM_REG_R0);b=uc.reg_read(UC_ARM_REG_R1);c=uc.reg_read(UC_ARM_REG_R2);result=0
  if pc==0x6cc0:result=HEAP+state['alloc'];state['alloc']+=(a+15)&~15
  elif pc in [0x8316,0x6f2c,0x532,0x4e6c]:pass
  elif pc==0x6d14:state['freed'].append(a)
  elif pc==0x25bf0:
   uc.mem_write(a,bytes(uc.mem_read(b,c)));state['copies'].append(c);result=a
  elif pc==0x107ca:
   assert b==0x07420000 and c==4096;state['maps'].append([b,c]);uc.mem_write(LIST,struct.pack('<II',NODE,NODE));uc.mem_write(INFO,struct.pack('<6I',b,c,VMM,INFO,0,0));uc.mem_write(VMM,struct.pack('<I',0x12345678))
  elif pc==0x645c:assert a==LIST and b==NODE;uc.mem_write(LIST,bytes(8))
  elif pc==0x843c:assert a==0x12345678
  elif pc==0x8352:state['queued'].append([a,b,c]);assert a==0x12345678 and b==0
  elif pc==0x1ba40:
   length=struct.unpack('<I',uc.mem_read(b,4))[0];state['packets'].append(bytes(uc.mem_read(b,length)))
  else:raise RuntimeError('Unexpected IO provider '+hex(pc))
  uc.reg_write(UC_ARM_REG_R0,result);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
 u.hook_add(UC_HOOK_CODE,step)
 def call(entry,r0,r1=0,r2=0):
  for reg,value in [(UC_ARM_REG_SP,STACK+0xf000),(UC_ARM_REG_LR,STOP|1),(UC_ARM_REG_R0,r0),(UC_ARM_REG_R1,r1),(UC_ARM_REG_R2,r2)]:u.reg_write(reg,value)
  u.emu_start(entry,STOP,timeout=1000000,count=200000);assert u.reg_read(UC_ARM_REG_PC)==STOP
 call(0x1c855,DATA+0x200,DATA,operation!='config')
 if operation=='config':
  assert len(state['queued'])==1 and state['copies']==[1216,1216] and not state['packets'];command=state['queued'][0][2]
  assert bytes(u.mem_read(command+8,1216))==bytes(payload)
  callback=struct.unpack('<I',u.mem_read(command+1240,4))[0];u.mem_write(DATA+0x300,struct.pack('<IIQ I',0,65536,0x13579bdf2468ace0,callback));call(0x1eacf,DATA+0x300)
  expected_bytes=56;expected_type=0x102000e
 else:
  expected_bytes=44;expected_type=0x102000a
  assert not state['queued']
  if operation=='map':assert state['maps']==[[0x7420000,4096]]
  else:assert struct.unpack('<I',u.mem_read(LIST,4))[0]==0
 assert len(state['packets'])==1;reply=state['packets'][0]
 assert struct.unpack_from('<IIIQQI',reply)==(expected_bytes,expected_type,opcode,*tokens,0)
 assert struct.unpack_from('<I',reply,32)[0]==0
 if operation=='config':assert struct.unpack_from('<I',reply,36)[0]==65536
 (P/(operation+'-reply-private.bin')).write_bytes(reply)
 rows.append(dict(operation=operation,command_bytes=len(packet),reply_bytes=len(reply),two_u64_tokens_echoed=True,original_async_dispatch_executed=True))
report=dict(stage=377,tests=rows,original_io_config_1216_byte_payload_copied_twice=True,config_ack_bytes=56,map_unmap_ack_bytes=44,
 config_returned_scratch_size_offset=36,user_arg_at_payload_end_verified=True,
 os_allocator_cache_log_stream_vmm_and_post_message_providers_mocked=True,config_processing_handler_and_real_vmm_not_executed=True,
 original_dispatch_check_command_size_and_response_callbacks_executed=True,no_hardware_execution_claim=True,passed=True)
(HERE/'firmware-io-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
