"""Execute the original SendSfrMessage body, with explicitly bounded providers."""
from pathlib import Path
import hashlib,json,struct
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_LR,UC_ARM_REG_PC,UC_ARM_REG_SP
import host
HERE=Path(__file__).resolve().parent;raw=(host.PRIVATE.parent/'kernel352/CAMERA_ICP.elf-private').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='a22bc8adbb4ae97e4f8d728eecb1fd19c1bf866250b0bb7e668951c41c159e63'
phoff=struct.unpack_from('<I',raw,28)[0];stride,count=struct.unpack_from('<HH',raw,42)
segments=[struct.unpack_from('<8I',raw,phoff+i*stride) for i in range(count)]
REG=0xe0010000;SHARED=0x07400000;SFR=SHARED+0x1c000;INPUT=0x05000000;STACK=0x02000000;STOP=0x04000000
profiles=[('idle',0,0,0,1),('bps-ok',1,0,0,1),('bps-error',1,0,1,1),('ipe-v1',0,1,0,1),('ipe-v2',0,1,0,2),('ipe-error',0,1,1,2),('both-v2',1,1,0,2)]
cases=[(n,b,i,e,c,4096,True) for n,b,i,e,c in profiles]
cases += [('short-'+str(n),0,0,0,1,n,True) for n in [0,4,5]]
cases += [('no-sfr',0,0,0,1,4096,False)]
records=[]
for name,bps,ipe,power_error,chip,sfr_size,has_sfr in cases:
 u=Uc(UC_ARCH_ARM,UC_MODE_THUMB);maximum=(max(s[2]+s[5] for s in segments if s[0]==1)+4095)&~4095;u.mem_map(0,maximum)
 for kind,offset,va,pa,filesz,memsz,flags,align in segments:
  if kind==1:u.mem_write(va,raw[offset:offset+filesz])
 for addr,size in [(REG,4096),(SHARED,0x20000),(INPUT,0x2000),(STACK,0x10000),(STOP,4096)]:u.mem_map(addr,size)
 u.mem_write(REG+0x4c,struct.pack('<I',1));u.mem_write(REG+0x68,struct.pack('<I',SFR if has_sfr else 0))
 u.mem_write(SFR,struct.pack('<I',sfr_size));u.mem_write(INPUT,b'synthetic fault\0');u.mem_write(INPUT+0x1008,struct.pack('<I',chip))
 for addr,value in [(0x126d08,bps),(0x126d07,ipe)]:u.mem_write(addr,bytes([value]))
 for addr,value in [(0x126d28,bps),(0x126d24,ipe),(0x120938,INPUT+0x1000 if ipe else 0)]:u.mem_write(addr,struct.pack('<I',value))
 state=dict(instructions=0,responses=[],cache_calls=[],power_calls=[],events=[],formatted=False)
 def cstring(addr):
  out=bytearray()
  while len(out)<256:
   b=u.mem_read(addr+len(out),1)
   if b==b'\0':return bytes(out)
   out.extend(b)
  raise RuntimeError('Unterminated synthetic string')
 def step(uc,pc,size,user):
  state['instructions']+=1
  if 0x1b8a4<=pc<0x1ba00:return
  r0=uc.reg_read(UC_ARM_REG_R0);r1=uc.reg_read(UC_ARM_REG_R1);r2=uc.reg_read(UC_ARM_REG_R2);r3=uc.reg_read(UC_ARM_REG_R3);result=0
  if pc==0x224c4:
   state['power_calls'].append([r0,r1]);result=power_error
  elif pc==0x6f2c:
   words=list(struct.unpack('<4I',uc.mem_read(r0,16)));state['cache_calls'].append(words);state['events'].append('cache-'+str(words[1]))
  elif pc==0x25b3e:
   assert r0==SFR+4 and r1==sfr_size-4 and r3==INPUT and b'%s' in cstring(r2)
   message=cstring(r3);uc.mem_write(r0,message[:max(0,r1-1)]+b'\0');state['formatted']=True;state['events'].append('synthetic-format');result=len(message)
  elif pc==0x7e1c:
   assert r0==REG+0x4c and r1==3;state['events'].append('dump-register-3')
  elif pc==0x8316:pass
  else:raise RuntimeError('Unexpected provider at '+hex(pc))
  uc.reg_write(UC_ARM_REG_R0,result);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
 def write(uc,access,address,size,value,user):
  if address==REG+0x4c:
   state['responses'].append(dict(value=value,pc=uc.reg_read(UC_ARM_REG_PC),bytes=size));state['events'].append('publish-response-'+str(value))
 u.hook_add(UC_HOOK_CODE,step);u.hook_add(UC_HOOK_MEM_WRITE,write)
 u.reg_write(UC_ARM_REG_R0,INPUT);u.reg_write(UC_ARM_REG_SP,STACK+0xf000);u.reg_write(UC_ARM_REG_LR,STOP|1)
 u.emu_start(0x1b8a5,STOP,timeout=1000000,count=10000)
 assert u.reg_read(UC_ARM_REG_PC)==STOP
 assert state['responses']==[dict(value=3,pc=0x1b9f2,bytes=4)]
 assert struct.unpack('<I',u.mem_read(REG+0x4c,4))[0]==3
 assert state['formatted']==bool(has_sfr and sfr_size>=5)
 assert state['events'][-2:]==['dump-register-3','publish-response-3']
 if state['formatted']:assert state['events'].index('synthetic-format')<state['events'].index('publish-response-3')
 records.append(dict(case=name,instructions=state['instructions'],power_calls=state['power_calls'],cache_provider_calls=len(state['cache_calls']),format_provider_called=state['formatted'],actual_response=3,store_pc='0x1b9f2',passed=True))
report=dict(stage=368,firmware_sha256=hashlib.sha256(raw).hexdigest(),actual_original_function='SendSfrMessage',entry='0x1b8a5',bytes=348,
    tests=records,response_three_is_published_by_sfr_error_path=True,exact_csr_address='0xe001004c',
    valid_sfr_buffer_formatted_before_response_publication=True,response_three_is_not_initialization_success=True,
    log_cache_format_and_core_power_providers_mocked=True,no_claim_to_simulate_real_cache_power_or_scheduler=True,
    exact_device_failure_string_not_recovered_by_this_test=True,hardware_accessed=False,passed=True)
(HERE/'firmware-sfr-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='tests'},indent=2))
