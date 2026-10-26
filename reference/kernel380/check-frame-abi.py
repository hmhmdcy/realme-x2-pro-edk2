"""Run original frame dispatch/copy/callback with a real offline stripe result."""
from pathlib import Path
import json,struct
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
HERE=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel380')
prefix=(HERE.parent/'kernel379/check-firmware-io.py').read_text().split("for operation in ['map','unmap','config']:")[0]
scope=dict(__file__=str(HERE/'check-frame-abi.py'));exec(compile(prefix,'original-firmware-machine','exec'),scope)
DATA=scope['DATA'];HEAP=scope['HEAP'];STACK=scope['STACK'];STOP=scope['STOP'];tokens=scope['tokens'];rows=[]
hal=(P/'hal-process-request-private.asm').read_text();assert 'str\tx6, [x20, #3808]' in hal
for row in json.loads((P/'striping-cases-private.json').read_text()):
 u=scope['machine']();frame_address=DATA+0x2000;stripe_address=DATA+0x4000;iq_address=DATA+0x9000;callback_input=DATA+0x1000
 stripe=Path(row['stripe']).read_bytes();assert len(stripe)<0x5000
 u.mem_write(stripe_address,stripe);u.mem_write(iq_address,Path(row['iq']).read_bytes())
 frame=(P/(row['slug']+'-encoded-frame-private.bin')).read_bytes();assert len(frame)==3816
 assert struct.unpack_from('<II',frame)==(stripe_address,iq_address);u.mem_write(frame_address,frame)
 packet=struct.pack('<IIIQQIII',40,0x101000e,6,*tokens,1,0x12345678,frame_address);u.mem_write(DATA,packet)
 # Provider-owned automatic engine power collapse is outside this dispatch model.
 u.mem_write(0x126d07,b'\0');state=dict(alloc=0,allocations=[],copies=[],cache=[],queued=[],packets=[],freed=[])
 def step(uc,pc,size,user):
  if 0x1c854<=pc<0x1e9d2 or 0x1eaf2<=pc<0x1eba0 or 0x1ec0c<=pc<0x1ecd6:return
  a=uc.reg_read(UC_ARM_REG_R0);b=uc.reg_read(UC_ARM_REG_R1);c=uc.reg_read(UC_ARM_REG_R2);result=0
  if pc==0x6cc0:
   result=HEAP+state['alloc'];state['alloc']+=(a+15)&~15;assert state['alloc']<0x10000
   uc.mem_write(result,bytes([0xa5])*a);state['allocations'].append([result,a])
  elif pc==0x6f2c:state['cache'].append(struct.unpack('<4I',uc.mem_read(a,16)))
  elif pc in [0x8316]:pass
  elif pc==0x6d14:state['freed'].append(a)
  elif pc==0x25bf0:uc.mem_write(a,bytes(uc.mem_read(b,c)));state['copies'].append([a,b,c]);result=a
  elif pc==0x8352:assert a==0x12345678 and b==1;state['queued'].append(c)
  elif pc==0x1ba40:state['packets'].append(bytes(uc.mem_read(b,struct.unpack('<I',uc.mem_read(b,4))[0])))
  else:raise RuntimeError('Unexpected frame provider '+hex(pc))
  uc.reg_write(UC_ARM_REG_R0,result);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
 u.hook_add(UC_HOOK_CODE,step)
 def call(entry,a,b=0,c=0):
  for reg,value in [(UC_ARM_REG_SP,STACK+0xf000),(UC_ARM_REG_LR,STOP|1),(UC_ARM_REG_R0,a),(UC_ARM_REG_R1,b),(UC_ARM_REG_R2,c)]:u.reg_write(reg,value)
  u.emu_start(entry,STOP,timeout=1000000,count=200000);assert u.reg_read(UC_ARM_REG_PC)==STOP
 call(0x1c855,DATA+0x800,DATA,0);assert len(state['queued'])==1 and not state['packets'];command=state['queued'][0]
 assert [struct.unpack_from('<I',u.mem_read(command+8+off,4))[0] for off in [0,4,8,12,32,36,84,88]]==[stripe_address,iq_address,0x20000000,48,struct.unpack_from('<I',frame,32)[0],1000000,1,1]
 assert struct.unpack('<I',u.mem_read(command+36,4))[0]==struct.unpack_from('<I',frame,28)[0]-32
 assert bytes(u.mem_read(command+8+92,232))==bytes(frame[92:324])
 cb=struct.unpack('<I',u.mem_read(command+3816,4))[0];assert cb
 callback_payload=struct.pack('<IIQ4I',0,0x20000000,0x13579bdf2468ace0,11,22,33,44)
 u.mem_write(callback_input,callback_payload+struct.pack('<I',cb));call(0x1eaf3,callback_input)
 assert len(state['packets'])==1;reply=state['packets'][0]
 assert struct.unpack_from('<IIIQQI',reply)==(72,0x102000e,6,*tokens,0)
 assert reply[32:]==callback_payload+bytes(8)
 assert any(length==324 for _,_,length in state['copies']) and any(address==frame_address and size==3816 for op,flag,address,size in state['cache'])
 assert any(address==iq_address and size==2584 for op,flag,address,size in state['cache']) and any(address==stripe_address and size==row['used_bytes'] for op,flag,address,size in state['cache'])
 (P/(row['slug']+'-frame-packet-private.bin')).write_bytes(packet);(P/(row['slug']+'-frame-payload-private.bin')).write_bytes(frame);(P/(row['slug']+'-frame-ack-private.bin')).write_bytes(reply)
 rows.append(dict(case=row['slug'],command_bytes=40,frame_payload_bytes=3816,single_frame_copy_bytes=324,iq_cache_bytes=2584,stripe_cache_bytes=row['used_bytes'],frame_reply_bytes=72,passed=True))
report=dict(stage=380,tests=rows,original_dispatch_size_checks_pointer_fixups_and_frame_callback_executed=True,
 original_hal_generated_stripe_and_actual_c_builder_output_consumed=True,frame_header_bytes=92,frame_set_bytes=232,image_ports=14,planes=2,max_batch=16,
 frame_user_arg_offset=3808,user_arg_offset_from_retained_hal_store_instruction_not_full_hal_request_execution=True,frame_callback_copies_32_bytes_then_zeroes_8=True,
 allocator_cache_log_stream_queue_and_post_message_providers_modelled=True,automatic_engine_power_collapse_branch_disabled=True,
 real_engine_frame_handler_and_pixel_dma_not_executed=True,hardware_execution=False,passed=True)
(HERE/'frame-abi-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
