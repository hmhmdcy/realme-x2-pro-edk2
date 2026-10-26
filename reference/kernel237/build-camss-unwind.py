"""Build the full fae1+unwind module, then restore canonical after228 exactly."""
from pathlib import Path
import hashlib,importlib.util,json,os,re,shutil,stat,subprocess,time
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel237');K=Path('/home/cy122/pmos-samurai-kernel136/kernel')
spec=importlib.util.spec_from_file_location('snapshot227',R.parent/'kernel227/prepare-fastrpc.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
before=helper.snapshot();assert before==json.loads((P.parent/'kernel228/canonical-after-private.json').read_text())
out=P/'camss-build-r1';assert not out.exists();out.mkdir(mode=0o700)
directories=[K/'drivers/media/platform/qcom/camss',K/'drivers/media/common/videobuf2']
names=['.config','.config.old','Module.symvers','modules.order','include/generated/compile.h','include/generated/utsrelease.h','include/generated/utsversion.h','include/generated/autoconf.h','include/config/auto.conf','include/config/auto.conf.cmd','include/config/kernel.release']
files={p for d in directories for p in d.iterdir() if p.is_file() and not p.is_symlink()}|{K/n for n in names if (K/n).is_file()}
saved={str(p.relative_to(K)):(p.read_bytes(),stat.S_IMODE(p.stat().st_mode)) for p in files}
for n,(data,mode) in saved.items():p=out/'before'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);p.chmod(mode)
proof=json.loads((R/'camss-source-validation.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
env=dict(os.environ,KBUILD_BUILD_VERSION='183',PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup')
ret=None;start=time.monotonic();module=out/'qcom-camss-unwind237.ko'
try:
 for name,digest in proof['candidate_sources'].items():
  source=R/'camss-source'/name;assert sha(source)==digest;shutil.copyfile(source,directories[0]/name)
 cmd=['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LD=aarch64-linux-gnu-ld --no-keep-memory','W=1','-j3',*['drivers/media/common/videobuf2/videobuf2-'+n+'.ko' for n in ['common','memops','v4l2','dma-sg']],'drivers/media/platform/qcom/camss/qcom-camss.ko']
 with (out/'build-private.log').open('xb') as log:ret=subprocess.run(cmd,cwd=K,env=env,stdout=log,stderr=subprocess.STDOUT).returncode
 if ret==0:
  shutil.copyfile(directories[0]/'qcom-camss.ko',module);subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(module)],check=True)
finally:
 for p in {p for d in directories for p in d.iterdir() if p.is_file() and not p.is_symlink()}|{K/n for n in names}:
  if p.is_file() and str(p.relative_to(K)) not in saved:p.unlink()
 for n,(data,mode) in saved.items():p=K/n;p.write_bytes(data);p.chmod(mode)
 restored=helper.snapshot()==before
 (out/'restoration-private.json').write_text(json.dumps(dict(build_exit=ret,canonical_after228_restored=restored),indent=2)+'\n');assert restored
assert ret==0,'Inspect private build log; canonical restored'
assert not re.search(r'\b(warning|error):',(out/'build-private.log').read_text(),re.I)
info=lambda key:subprocess.check_output(['modinfo','-F',key,str(module)],text=True).strip()
assert info('intree')=='Y' and info('vermagic')=='7.3.0-rc6-rmx1931-samurai-k132+ SMP preempt mod_unload aarch64'
available={line.split()[1] for line in saved['Module.symvers'][0].decode().splitlines()}
imports={line.split()[-1] for line in subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(module)],text=True).splitlines() if line.strip()};assert imports<=available
report=dict(stage=237,sha256=sha(module),bytes=module.stat().st_size,intree=True,vermagic=info('vermagic'),source_inputs=proof['candidate_sources'],w1_diagnostics=0,imports_available=True,canonical_after228_restored=True,elapsed_seconds=round(time.monotonic()-start,2),hardware_not_loaded_yet=True)
(R/'camss-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
