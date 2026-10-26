"""Compile camera targets from the maintained tree into a fresh output directory."""
from pathlib import Path
import hashlib,json,os,re,resource,shutil,subprocess,time,sys
R=Path(__file__).resolve().parent;U=Path('/home/cy122/x2pro-linux/upstream');K=Path('/home/cy122/pmos-samurai-kernel136/kernel')
B=Path('/home/cy122/x2pro-linux/camera268-maintained-build-r2');audit=sys.argv[1:]==['--audit-existing']
assert not sys.argv[1:] or audit
if not audit:
 B.mkdir(mode=0o700);shutil.copyfile(K/'.config',B/'.config')
 subprocess.run([str(U/'scripts/config'),'--file',str(B/'.config'),'--module','VIDEO_IMX319'],check=True)
env=dict(os.environ,PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup',KBUILD_BUILD_VERSION='183')
base=['make','-C',str(U),'O='+str(B),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LD=aarch64-linux-gnu-ld --no-keep-memory','-j3']
steps=json.loads((B/'state-private.json').read_text()) if audit else []
def limit():resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
def run(name,extra):
 t=time.monotonic()
 with (B/(name+'-private.log')).open('xb') as log:q=subprocess.run(base+extra,env=env,stdout=log,stderr=subprocess.STDOUT,preexec_fn=limit)
 steps.append(dict(step=name,exit=q.returncode,seconds=round(time.monotonic()-t,2)))
 (B/'state-private.json').write_text(json.dumps(steps)+'\n')
 assert q.returncode==0,'Inspect '+name+' log; do not reuse this output for another run'
if not audit:
 run('configure',['olddefconfig'])
 run('prepare',['modules_prepare'])
# Compile the exact source targets. A complete module link needs a fresh vmlinux.o;
# copied Module.symvers alone is deliberately insufficient for in-tree modpost.
targets=['drivers/mfd/qcom-pm8008.o','drivers/regulator/qcom-pm8008-regulator.o',
 'drivers/media/i2c/imx319.o','drivers/media/i2c/imx471.o','drivers/media/platform/qcom/camss/qcom-camss.o']
if not audit:run('camera',['W=1',*targets,'qcom/sm8150-samurai.dtb'])
assert len(steps)==3 and all(s['exit']==0 for s in steps)
log=(B/'camera-private.log').read_text();diagnostics=[l for l in log.splitlines() if re.search(r'\b(warning|error):',l,re.I)]
assert not diagnostics,diagnostics
for n,digest in json.loads((R/'maintained-source-validation.json').read_text())['source_files_sha256'].items():
 assert hashlib.sha256((U/n).read_bytes()).hexdigest()==digest
modules={}
available={l.split()[1] for l in (K/'Module.symvers').read_text().splitlines()}
for n in targets:
 p=B/n
 imports={l.split()[-1] for l in subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(p)],text=True).splitlines() if l.strip()}
 # __this_module is supplied by generated .mod.c at the later module link.
 assert imports<=available|{'__this_module'},imports-available-{'__this_module'}
 modules[n]=dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),external_imports_in_deployed_abi=True,
  generated_module_metadata_symbol_expected='__this_module' in imports)
dtb=B/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'
report=dict(stage=268,steps=steps,compiled_objects=modules,w1_camera_diagnostics=0,dtc_diagnostics=[l for l in log.splitlines() if 'Warning (' in l],dtb_sha256=hashlib.sha256(dtb.read_bytes()).hexdigest(),
 dtb_matches_deployed267=dtb.read_bytes()==Path('/mnt/e/edk2-samurai-out/kernel267/board-build-r1/sm8150-samurai.dtb').read_bytes(),
 fresh_out_of_tree_output=True,all_camera_sources_exact=True,imports_checked_against_deployed183_symbol_list=True,
 first_attempt_modpost_rejected_missing_vmlinux=True,full_module_link_not_repeated=True,
 full_image_and_all_modules_not_rebuilt=True,candidate_not_deployed=True)
(R/'maintained-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
