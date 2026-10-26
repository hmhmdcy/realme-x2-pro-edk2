"""Execute the original HAL image descriptor encoder for ordinary linear NV12."""
from pathlib import Path
import hashlib,json,struct
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_INTR
from unicorn.arm64_const import *
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;raw=(P.parent/'kernel281/camera.qcom.so-private').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde'
phoff=struct.unpack_from('<Q',raw,32)[0];stride,count=struct.unpack_from('<HH',raw,54);segments=[struct.unpack_from('<II6Q',raw,phoff+i*stride) for i in range(count)]
OBJECT=0x1000000;OUT=0x5000000;STACK=0x2000000;TLS=0x3000000;STOP=0x4000000
u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);maximum=(max(s[3]+s[6] for s in segments if s[0]==1)+4095)&~4095;u.mem_map(0,maximum)
for kind,flags,off,va,pa,filesz,memsz,align in segments:
 if kind==1:u.mem_write(va,raw[off:off+filesz])
for address,size in [(OBJECT,0x10000),(OUT,0x10000),(STACK,0x10000),(TLS,4096),(STOP,4096)]:u.mem_map(address,size)
u.reg_write(UC_ARM64_REG_CPACR_EL1,3<<20);u.reg_write(UC_ARM64_REG_TPIDR_EL0,TLS);instructions=[0]
def step(uc,pc,size,user):
 instructions[0]+=1
 if not 0x2e4b88<=pc<0x2e4f00:raise RuntimeError('Unexpected HAL provider '+hex(pc))
def interrupt(uc,number,user):raise RuntimeError('Unexpected emulated exception '+str(number))
u.hook_add(UC_HOOK_CODE,step);u.hook_add(UC_HOOK_INTR,interrupt);rows=[];records=[]
for port in [0,8,9]:
 for swap in [False,True]:
  for width,height,stride,slice_height in [(640,480,640,480),(1920,1080,1920,1088),(1280,720,1344,736)]:
   image=OBJECT+0x1000;u.mem_write(image,bytes(256));u.mem_write(image,struct.pack('<III',width,height,4 if swap else 3))
   u.mem_write(image+32,struct.pack('<4I',stride,slice_height,0,0));u.mem_write(image+72,struct.pack('<4I',stride,slice_height//2,0,0));u.mem_write(OUT,bytes(1216))
   for reg,value in [(UC_ARM64_REG_X0,OBJECT),(UC_ARM64_REG_X1,OUT),(UC_ARM64_REG_X2,image),(UC_ARM64_REG_X3,port),(UC_ARM64_REG_X4,OBJECT+0x2000),(UC_ARM64_REG_LR,STOP),(UC_ARM64_REG_SP,STACK+0xf000)]:u.reg_write(reg,value)
   u.emu_start(0x2e4b88,STOP,timeout=1000000,count=10000);assert u.reg_read(UC_ARM64_REG_PC)==STOP
   actual=bytes(u.mem_read(OUT,1216));expected=bytearray(1216);offset=port*84
   struct.pack_into('<III',expected,offset,20,width,height);struct.pack_into('<I',expected,offset+24,int(swap));struct.pack_into('<4I',expected,offset+52,stride,slice_height,stride,slice_height//2)
   assert actual==expected,(port,swap,width)
   records.append(dict(port=port,swap=swap,width=width,height=height,stride=stride,slice_height=slice_height,data_hex=actual.hex()))
   rows.append(dict(port=port,swap=swap,width=width,height=height,matched=True))
(P/'hal-io-cases-private.json').write_text(json.dumps(records)+'\n')
# The whole setup is not executed. These exact retained setup instructions
# independently fix userArg, secure mode, batch and margins byte positions.
setup=(P/'hal-setup-private.asm').read_text();assert all(s in setup for s in ['str\txzr, [x24, #1208]','str\tw9, [x24, #1184]','str\tw11, [x23, #1192]','str\tx2, [x1, #1176]'])
report=dict(stage=377,original_complete_hal_set_config_io_data_executed=True,tests=rows,instructions=instructions[0],external_providers_mocked=False,
 image_descriptor_stride=84,format_linear_nv12=20,format_width_height_offsets=[0,4,8],uv_swap_offset=24,buffer_layout_offset=52,
 metadata_layout_offset=68,user_arg_offset=1208,secure_mode_offset=1184,max_batch_size_offset=1192,stabilization_margins_offset=1176,
 top_level_positions_from_exact_original_setup_instructions_not_full_setup_execution=True,no_hardware_execution_claim=True,passed=True)
(HERE/'hal-io-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='tests'},indent=2))
