"""Enforce a live Gamma SRAM clock in the actual processing/lifecycle harness."""
from pathlib import Path
import hashlib,json,re,subprocess
import host

ROOT=Path(__file__).resolve().parent;TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
old=Path('/mnt/e/edk2-samurai-out/kernel288/demux-mnds-host-tests-private.c').read_text()
gamma=(TREE/'drivers/media/platform/qcom/camss/camss-vfe-175-gamma.c').read_text()
def replace_function(text,source,name):
 pattern=r'int '+name+r'\(.*?\n\}'
 actual=re.search(pattern,source,re.S);assert actual
 existing=re.search(pattern,text,re.S);assert existing
 return text[:existing.start()]+actual[0]+text[existing.end():]
s=replace_function(old,gamma,'vfe_175_gamma_configure')
s=s.replace('#define VFE_175_COLOR_ENABLE','#define VFE_175_COLOR_CGC_OVERRIDE 0x034\n#define VFE_175_COLOR_ENABLE',1)
s=s.replace('u32 cfg,index;memcpy(&cfg,bank+0xc24,4);','u32 cfg,index,clock;memcpy(&clock,bank+0x34,4);assert(clock & 8);memcpy(&cfg,bank+0xc24,4);')
s=s.replace('writes==391 && barriers==2 && nt==393','writes==393 && barriers==2 && nt==395')
s=s.replace('trace[ch*129+1+i*2]==0xc28 && trace[ch*129+2+i*2]==0xc30','trace[ch*129+2+i*2]==0xc28 && trace[ch*129+3+i*2]==0xc30')
s=s.replace('trace[387]==0xc24 && trace[388]==0xc28 && trace[389]==0xffff && trace[390]==0x798 && trace[391]==0xffff && trace[392]==0x48',
 'trace[0]==0x34 && trace[388]==0xc24 && trace[389]==0xc28 && trace[390]==0xffff && trace[391]==0x798 && trace[392]==0x34 && trace[393]==0xffff && trace[394]==0x48 && get(0x34)==0xa5a5a5a5U')
s=s.replace('writes==449 && v.pixel175.wb_enabled','writes==451 && v.pixel175.wb_enabled')
needle='c=base;c.enabled=false;reset_trace();dmi_writes=0;'
assert s.count(needle)==1
s=s.replace(needle,'''for(unsigned state=0;state<4;state++){
  u32 saved=state==0?0:state==1?8:state==2?0x5a5a5a5aU:0xa5a5a5a5U;
  memcpy(bank+0x34,&saved,4);reset_trace();assert(!vfe_175_gamma_configure(v,&base));assert(get(0x34)==saved);
 }
 '''+needle)
p=host.PRIVATE/'gamma-clock-tests-private.c';p.write_text(s)
binary=host.PRIVATE/'gamma-clock-tests-private'
flags=['gcc','-std=gnu11','-O1','-g','-Wall','-Werror','-Wno-misleading-indentation','-D__EXPORTED_HEADERS__','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include','-I'+str(TREE/'include/uapi')]
q=subprocess.run(flags+[str(p),'-lm','-o',str(binary)],capture_output=True)
log=host.PRIVATE/'gamma-clock-tests-compile-private.log'
if log.exists():
 i=1
 while log.with_suffix('.log.attempt'+str(i)).exists():i+=1
 log.with_suffix('.log.attempt'+str(i)).write_bytes(log.read_bytes())
log.write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
q=subprocess.run([str(binary)],capture_output=True,timeout=60)
(host.PRIVATE/'gamma-clock-tests-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
original=subprocess.check_output(['git','-C',str(TREE),'show','HEAD:drivers/media/platform/qcom/camss/camss-vfe-175-gamma.c'],text=True)
negative=host.PRIVATE/'gamma-clock-negative-private.c';negative.write_text(replace_function(s,original,'vfe_175_gamma_configure'))
nbinary=host.PRIVATE/'gamma-clock-negative-private'
q2=subprocess.run(flags+[str(negative),'-lm','-o',str(nbinary)],capture_output=True);assert q2.returncode==0,q2.stderr.decode()
q2=subprocess.run([str(nbinary)],capture_output=True,timeout=60)
(host.PRIVATE/'gamma-clock-negative-private.log').write_bytes(q2.stdout+q2.stderr)
assert q2.returncode!=0 and b'clock & 8' in q2.stderr
report=dict(stage=289,asan_ubsan=True,actual_gamma_and_processing_lifecycle=True,all_dmi_writes_require_gamma_clock=True,
 original_code_negative_control_failed_on_clock_requirement=True,clock_policy_restored_all_four_patterns=True,
 inactive_bank_and_shared_dmi_state_preserved=True,existing_processing_tests_retained=True,
 gamma_source_sha256=hashlib.sha256(gamma.encode()).hexdigest(),harness_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
 output=q.stdout.decode().strip(),not_deployed=True)
(ROOT/'gamma-clock-host-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
