"""Reproduce the command mapping conflict through original firmware functions."""
from pathlib import Path
import json,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
prefix=(HERE/'check-firmware-io.py').read_text().split("for operation in ['map','unmap','config']:")[0]
scope=dict(__file__=str(HERE/'check-queue-overlap.py'));exec(compile(prefix,'firmware-machine-prefix','exec'),scope)
u=scope['machine']();DATA=scope['DATA'];LIST=scope['LIST'];INFO=scope['INFO'];NODE=scope['NODE'];VMM=scope['VMM'];STACK=scope['STACK'];STOP=scope['STOP'];HEAP=scope['HEAP'];tokens=scope['tokens']
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
REG=0xe0010000;TABLE=DATA+0x8000;OUT=DATA+0x9000;u.mem_map(REG,4096);u.mem_write(REG+0x58,struct.pack('<I',TABLE));u.mem_write(0x109b80,struct.pack('<I',LIST))
u.mem_write(TABLE,struct.pack('<6I',0xffffffff,2892,24,956,3,3))
for index,words in enumerate([1024,1024,25600]):
 for offset,value in [(60,1),(124,0x07400000+[0x1000,0x2000,0x3000][index]),(188,index),(252,words)]:u.mem_write(TABLE+24+index*956+offset,struct.pack('<I',value))
state=dict(phase='queues',maps=[],packets=[],alloc=0)
def step(uc,pc,size,user):
 if 0x1a970<=pc<0x1aa10 or 0x1c854<=pc<0x1e9d2 or 0x1ec0c<=pc<0x1ecd6:return
 a=uc.reg_read(UC_ARM_REG_R0);b=uc.reg_read(UC_ARM_REG_R1);c=uc.reg_read(UC_ARM_REG_R2);result=0
 if pc==0x107ca:state['maps'].append([b,c])
 elif pc==0x246fa:assert a==1
 elif pc==0x6cc0:result=HEAP+state['alloc'];state['alloc']+=(a+15)&~15
 elif pc in [0x8316,0x6f2c,0x6d14]:pass
 elif pc==0x1ba40:state['packets'].append(bytes(uc.mem_read(b,struct.unpack('<I',uc.mem_read(b,4))[0])))
 else:raise RuntimeError('Unexpected overlap provider '+hex(pc))
 uc.reg_write(UC_ARM_REG_R0,result);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
u.hook_add(UC_HOOK_CODE,step)
def call(entry,r0,r1=0,r2=0):
 for reg,value in [(UC_ARM_REG_SP,STACK+0xf000),(UC_ARM_REG_LR,STOP|1),(UC_ARM_REG_R0,r0),(UC_ARM_REG_R1,r1),(UC_ARM_REG_R2,r2)]:u.reg_write(reg,value)
 u.emu_start(entry,STOP,timeout=1000000,count=100000);assert u.reg_read(UC_ARM_REG_PC)==STOP
for queue in range(3):call(0x1a971,queue,OUT)
assert state['maps']==[[TABLE,4096],[0x7401000,4096],[TABLE,4096],[0x7402000,4096],[TABLE,4096],[0x7403000,1048576]]
debug_start,debug_bytes=state['maps'][-1];rows=[]
for address in [0x07420000,0x07600000]:
 u.mem_write(LIST,struct.pack('<II',NODE,NODE));u.mem_write(INFO,struct.pack('<6I',debug_start,debug_bytes,VMM,INFO,0,0));u.mem_write(VMM,struct.pack('<I',0x1234))
 packet=struct.pack('<IIIQQIIQIII',56,0x101000a,14,*tokens,1,0x12345678,0,1,address,4096);u.mem_write(DATA,packet);before=len(state['maps']);state['packets']=[]
 call(0x1c855,DATA+0x200,DATA,1);assert len(state['packets'])==1
 reply=state['packets'][0];header=struct.unpack_from('<IIIQQI',reply);payload_error=struct.unpack_from('<I',reply,32)[0]
 rejected=bool(header[-1] or payload_error);assert rejected==(address==0x07420000)
 assert (len(state['maps'])==before)==rejected
 (P/('overlap-'+hex(address)+'-reply-private.bin')).write_bytes(reply)
 rows.append(dict(config_address=hex(address),bytes=4096,rejected=rejected,vmm_mapping_provider_called=not rejected,reply_bytes=len(reply),header_error=header[-1],payload_error=payload_error))
report=dict(stage=377,original_queue_lookup_and_async_map_overlap_checker_executed=True,
 debug_queue_storage_bytes=102400,debug_firmware_mapping_start=hex(debug_start),debug_firmware_mapping_bytes=debug_bytes,
 old_command_slot_overlaps_firmware_debug_mapping=True,separated_command_slot_is_outside_queue_mappings=True,tests=rows,
 mmu_allocator_cache_log_and_post_message_providers_mocked=True,preexisting_debug_region_modelled_from_original_mapping_request=True,
 explains_observed_377_explicit_map_rejection_but_exact_hardware_error_code_not_logged=True,
 no_hardware_test_of_new_slot_yet=True,passed=True)
(HERE/'queue-overlap-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
