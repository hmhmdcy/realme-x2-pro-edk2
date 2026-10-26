"""Check all native geometry combinations and the original dispatch fixups."""
from pathlib import Path
import importlib.util,json,struct
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('routing396',HERE/'probe-routing.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
command=(P/'cc-actual-private.bin').read_bytes()[:44];rows=[]
for width,height in [(640,480),(1920,1080),(4608,3456)]:
 for port in [8,9]:
  for cores in [1,2]:
   off,capacity,n=r.striping(width,height,port,cores,0);on,oncapacity,n2=r.striping(width,height,port,cores,1)
   assert off==on and capacity==oncapacity
   m,job,commands=r.prepare(on,width,height,port,cores,1,command)
   arrays=r.f.DATA+0x48000;external=[a for a,size in m.allocated.items() if size==12 and m.read32(a)==arrays+32]
   assert len(external)==1 and m.external.count(arrays+32)==1
   assert bytes(m.u.mem_read(arrays+128,44))==command
   enables=[struct.unpack_from('<II',commands,i) for i in range(0,len(commands)-8,4) if struct.unpack_from('<I',commands,i)[0]==0x5e60]
   assert enables==[(0x5e60,1)]
   rows.append(dict(width=width,height=height,port=port,cores=cores,striping_equal=True,bl_capacity=capacity,post_ltm_external_array_linked_once=True,post_ltm_cdm_bytes_preserved=True,colour_enable_register=0x5e60,colour_enable_value=1,hal_instructions=n+n2,firmware_instructions=m.instructions,passed=True))
prefix=(HERE.parent/'kernel379/check-firmware-io.py').read_text().split("for operation in ['map','unmap','config']:")[0]
scope=dict(__file__=str(HERE/'check-routing.py'));exec(compile(prefix,'original-dispatch','exec'),scope)
u=scope['machine']();D=scope['DATA'];HEAP=scope['HEAP'];STACK=scope['STACK'];STOP=scope['STOP'];tokens=scope['tokens'];state=dict(cursor=0,queued=[],cache=[])
frame=bytearray((P.parent/'kernel380/640x480-port8-cores1-encoded-frame-private.bin').read_bytes());arrays=D+0xa000;struct.pack_into('<I',frame,40,arrays);struct.pack_into('<I',frame,48,32)
u.mem_write(D+0x4000,(P.parent/'kernel380/640x480-port8-cores1-stripe-private.bin').read_bytes());u.mem_write(D+0x9000,(P.parent/'kernel382/hal-default-ica-iq-private.bin').read_bytes());u.mem_write(D+0x2000,bytes(frame));u.mem_write(arrays,bytes(128));u.mem_write(arrays+32,struct.pack('<8I',0,1,arrays+80,43<<12,0,0,0,0));u.mem_write(arrays+80,command)
u.mem_write(D,struct.pack('<IIIQQIII',40,0x101000e,6,*tokens,1,0x12345678,D+0x2000));u.mem_write(0x126d07,b'\0')
def step(uc,pc,size,user):
 if 0x1c854<=pc<0x1e9d2:return
 a=uc.reg_read(UC_ARM_REG_R0);b=uc.reg_read(UC_ARM_REG_R1);c=uc.reg_read(UC_ARM_REG_R2);result=0
 if pc==0x6cc0:
  result=HEAP+state['cursor'];state['cursor']+=(a+15)&~15;assert state['cursor']<0x10000;uc.mem_write(result,bytes([0xa5])*a)
 elif pc==0x6f2c:state['cache'].append(struct.unpack('<4I',uc.mem_read(a,16)))
 elif pc in [0x8316,0x6d14]:pass
 elif pc==0x25bf0:uc.mem_write(a,bytes(uc.mem_read(b,c)));result=a
 elif pc==0x8352:assert a==0x12345678 and b==1;state['queued'].append(c)
 else:raise RuntimeError('Unexpected dispatch provider '+hex(pc))
 uc.reg_write(UC_ARM_REG_R0,result);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
u.hook_add(UC_HOOK_CODE,step)
for reg,value in [(UC_ARM_REG_SP,STACK+0xf000),(UC_ARM_REG_LR,STOP|1),(UC_ARM_REG_R0,D+0x800),(UC_ARM_REG_R1,D),(UC_ARM_REG_R2,0)]:u.reg_write(reg,value)
u.emu_start(0x1c855,STOP,timeout=1000000,count=200000);assert u.reg_read(UC_ARM_REG_PC)==STOP and len(state['queued'])==1
queued=state['queued'][0];fixed=bytes(u.mem_read(queued+8,324));(P/'dispatch-fixed-header-private.bin').write_bytes(fixed)
(P/'dispatch-expected-private.json').write_text(json.dumps(dict(array_base=arrays,header_words=struct.unpack('<23I',fixed[:92]),cache=state['cache'])))
assert struct.unpack_from('<I',fixed,40)[0]==0 # Dispatcher clears base after relocation.
assert [struct.unpack_from('<I',fixed,i)[0] for i in range(44,84,4)]==[arrays+(32 if i==48 else 0) for i in range(44,84,4)]
assert any(a==arrays+32 and n==32 for op,flag,a,n in state['cache'])
report=dict(stage=396,cases=rows,geometry_cases=len(rows),original_hal_striping_with_cc_enabled_and_disabled_equal=True,original_complete_config_and_frame_preparation_executed=True,post_ltm_offset_field=48,program_array_base_field=40,dispatcher_clears_base_after_relocation=True,program_array_header_bytes=8,program_descriptor_bytes=24,post_ltm_program_type_generic=0,program_length_encoding='(command_bytes - 1) << 12 in high address/length word',original_complete_dispatch_fixups_and_array_cache_executed=True,all_ten_header_offsets_fixed_relative_to_base=True,os_allocator_cache_logs_stream_and_retirement_providers_only=True,stop_before_hardware_driver_enqueue=True,hardware_pixel_effect_not_verified=True,phone_changed=False,passed=True)
(HERE/'routing-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='cases'},indent=2))
