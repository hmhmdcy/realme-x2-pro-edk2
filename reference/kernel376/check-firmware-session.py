"""Original Thumb create handler and destroy callback; OS/stream providers mocked."""
from pathlib import Path
import hashlib,json,struct
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R5,UC_ARM_REG_R7,UC_ARM_REG_R9,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;raw=(P.parent/'kernel352/CAMERA_ICP.elf-private').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='a22bc8adbb4ae97e4f8d728eecb1fd19c1bf866250b0bb7e668951c41c159e63'
phoff=struct.unpack_from('<I',raw,28)[0];stride,count=struct.unpack_from('<HH',raw,42);segments=[struct.unpack_from('<8I',raw,phoff+i*stride) for i in range(count)]
STACK=0x02000000;STOP=0x04000000;HEAP=0x05000000;DATA=0x06000000
tokens=(0x1122334455667788,0x99aabbccddeeff00);rows=[]
def machine():
 u=Uc(UC_ARCH_ARM,UC_MODE_THUMB);maximum=(max(s[2]+s[5] for s in segments if s[0]==1)+4095)&~4095;u.mem_map(0,maximum)
 for kind,offset,va,pa,filesz,memsz,flags,align in segments:
  if kind==1:u.mem_write(va,raw[offset:offset+filesz])
 for address,size in [(STACK,0x10000),(STOP,4096),(HEAP,0x10000),(DATA,0x10000)]:u.mem_map(address,size)
 u.reg_write(UC_ARM_REG_SP,STACK+0xf000);u.reg_write(UC_ARM_REG_LR,STOP|1);return u
for kind in [2,3]:
 u=machine();u.mem_write(DATA,struct.pack('<IIIQQ',28,0x1010008,kind,*tokens));packets=[];calls=[]
 def step(uc,pc,size,user):
  if 0x1c470<=pc<0x1c854:return
  a=uc.reg_read(UC_ARM_REG_R0);b=uc.reg_read(UC_ARM_REG_R1);c=uc.reg_read(UC_ARM_REG_R2)
  if pc==0x25ef4:uc.mem_write(a,bytes([b&255])*c)
  elif pc==0xda70:
   assert b==1 and c==kind-2;uc.mem_write(a,struct.pack('<I',0x12345678+kind));uc.reg_write(UC_ARM_REG_R0,0);calls.append('create-stream')
  elif pc==0x8316:pass
  elif pc==0x1ba40:
   length=struct.unpack('<I',uc.mem_read(b,4))[0];packets.append(bytes(uc.mem_read(b,length)));uc.reg_write(UC_ARM_REG_R0,0)
  else:raise RuntimeError('Unexpected create provider '+hex(pc))
  uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
 u.hook_add(UC_HOOK_CODE,step);u.reg_write(UC_ARM_REG_R0,DATA+0x200);u.reg_write(UC_ARM_REG_R1,DATA);u.reg_write(UC_ARM_REG_R2,0x1010008)
 u.emu_start(0x1c471,STOP,timeout=1000000,count=100000)
 assert calls==['create-stream'] and len(packets)==1 and struct.unpack('<IIIIQQ',packets[0])==(32,0x1020008,0,0x12345678+kind,*tokens)
 (P/('create-type'+str(kind)+'-reply-private.bin')).write_bytes(packets[0]);rows.append(dict(operation='create',handle_type=kind,command_bytes=28,reply_bytes=32,full_original_handler_executed=True,two_u64_tokens_echoed=True))
for status in [0,0xa0001]:
 u=machine();u.mem_write(DATA,struct.pack('<IIIQQIIQ',44,0x101000a,8,*tokens,1,0x12345678,0x7a6b5c4d3e2f1001));packets=[];allocated=[];freed=[]
 def step(uc,pc,size,user):
  if 0x1d0ec<=pc<0x1d104 or 0x1e950<=pc<0x1e9d2 or 0x1ebbc<=pc<0x1ebee or 0x1ec0c<=pc<0x1ecd6:return
  a=uc.reg_read(UC_ARM_REG_R0);b=uc.reg_read(UC_ARM_REG_R1)
  if pc==0x6cc0:allocated.append(a);uc.reg_write(UC_ARM_REG_R0,HEAP)
  elif pc in [0x8316,0x6f2c]:pass
  elif pc==0x6d14:freed.append(a)
  elif pc==0x1ba40:
   length=struct.unpack('<I',uc.mem_read(b,4))[0];packets.append(bytes(uc.mem_read(b,length)));uc.reg_write(UC_ARM_REG_R0,0)
  else:raise RuntimeError('Unexpected destroy provider '+hex(pc))
  uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
 u.hook_add(UC_HOOK_CODE,step);u.reg_write(UC_ARM_REG_R5,DATA+0x200);u.reg_write(UC_ARM_REG_R7,DATA);u.reg_write(UC_ARM_REG_R9,1)
 u.emu_start(0x1d0ed,0x1d104,timeout=1000000,count=10000);callback=u.reg_read(UC_ARM_REG_R0);assert callback==HEAP and allocated==[68]
 u.mem_write(DATA+0x300,struct.pack('<III',status,0,callback));u.reg_write(UC_ARM_REG_R0,DATA+0x300);u.reg_write(UC_ARM_REG_SP,STACK+0xf000);u.reg_write(UC_ARM_REG_LR,STOP|1)
 u.emu_start(0x1ebbd,STOP,timeout=1000000,count=100000)
 assert len(packets)==1 and len(packets[0])==48 and freed==[HEAP]
 header=struct.unpack_from('<IIIQQI',packets[0]);assert header==(48,0x102000a,8,*tokens,0 if not status else 4),header
 assert struct.unpack_from('<I',packets[0],32)[0]==status
 (P/('destroy-status'+str(status)+'-reply-private.bin')).write_bytes(packets[0]);rows.append(dict(operation='destroy',status_nonzero=bool(status),reply_bytes=48,opcode=8,two_u64_tokens_echoed=True,original_caller_slice_allocator_callback_and_release_executed=True))
report=dict(stage=376,tests=rows,original_firmware_instructions_executed=True,stream_os_allocator_cache_log_and_post_message_providers_mocked=True,
 create_command_bytes=28,create_ack_bytes=32,destroy_command_bytes=44,destroy_ack_bytes=48,
 destroy_ack_has_16_byte_payload_despite_12_byte_packed_header_definition=True,destroy_payload_token_echo_not_required=True,
 no_hardware_execution_claim=True,raw_packets_and_assembly_private=True,passed=True)
(HERE/'firmware-session-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
