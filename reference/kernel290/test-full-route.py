"""Run actual FULL route/depth functions with existing processing and lifecycle tests."""
from pathlib import Path
import hashlib,json,re,subprocess
import host

ROOT=Path(__file__).resolve().parent;TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
old=Path('/mnt/e/edk2-samurai-out/kernel289/gamma-clock-tests-private.c').read_text()
round_source=(TREE/'drivers/media/platform/qcom/camss/camss-vfe-175-round.c').read_text()
def replace_function(text,source,signature):
 pattern=re.escape(signature)+r'\(.*?\n\}'
 actual=re.search(pattern,source,re.S);prior=re.search(pattern,text,re.S);assert actual and prior
 return text[:prior.start()]+actual[0]+text[prior.end():]
s=replace_function(old,round_source,'int vfe_175_round_configure')
s=replace_function(s,round_source,'void vfe_175_round_stop')
s=s.replace('#define VFE_175_FULL_Y_ENABLE','#define VFE_175_FRAME_ENABLE 0x04c\n#define VFE_175_FRAME_FULL_POST_PROCESS BIT(4)\n#define VFE_175_FULL_Y_ENABLE',1)
s=s.replace('writes==6 && barriers==1','writes==7 && barriers==2')
s=s.replace('nt==7 && trace[0]==0xe18','nt==9 && trace[0]==0xe18')
needle='trace[4]==0xffff && trace[5]==0xe0c && trace[6]==0xe2c'
s=s.replace(needle,needle+' && trace[7]==0xffff && trace[8]==0x4c')
needle='reset_trace();vfe_175_round_stop(v);assert(writes==2 && !(get(0xe0c)&0xc00) && !(get(0xe2c)&0xc00));'
assert s.count(needle)==1
s=s.replace(needle,'''assert((get(0x4c)&~16U)==(0xa5a5a5a5U&~16U) && !!(get(0x4c)&16)==(bool)on);
  reset_trace();vfe_175_round_stop(v);assert(writes==3 && !(get(0xe0c)&0xc00) && !(get(0xe2c)&0xc00) && !(get(0x4c)&16));
  assert((get(0x4c)&~16U)==(0xa5a5a5a5U&~16U));''')
s=s.replace('writes==451 && v.pixel175.wb_enabled','writes==452 && v.pixel175.wb_enabled')
p=host.PRIVATE/'full-route-tests-private.c';p.write_text(s);binary=host.PRIVATE/'full-route-tests-private'
flags=['gcc','-std=gnu11','-O1','-g','-Wall','-Werror','-Wno-misleading-indentation','-D__EXPORTED_HEADERS__','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include','-I'+str(TREE/'include/uapi')]
q=subprocess.run(flags+[str(p),'-lm','-o',str(binary)],capture_output=True)
(host.PRIVATE/'full-route-tests-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
q=subprocess.run([str(binary)],capture_output=True,timeout=60)
(host.PRIVATE/'full-route-tests-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
report=dict(stage=290,asan_ubsan=True,actual_round_configure_and_stop=True,full_route_gate_enabled_only_with_depth_processing=True,
 unrelated_frame_bits_preserved=True,invalid_inputs_zero_mmio=True,legacy_and_rdi_isolation=True,
 existing_gamma_cst_demux_mnds_demosaic_and_lifecycle_tests_retained=True,
 round_source_sha256=hashlib.sha256(round_source.encode()).hexdigest(),harness_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
 output=q.stdout.decode().strip(),not_deployed=True)
(ROOT/'full-route-host-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
