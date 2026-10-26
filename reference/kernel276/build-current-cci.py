"""Build the CCI resource fix for Image183 while restoring its original sources and outputs."""
from pathlib import Path
import hashlib,importlib.util,json,os,re,resource,shutil,stat,subprocess,time,sys
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE;K=Path('/home/cy122/pmos-samurai-kernel136/kernel');W=Path('/home/cy122/x2pro-linux/camera270-kernel');rel='drivers/i2c/busses/i2c-qcom-cci.c'
source=W/rel;proof=json.loads((R/'source-candidate-validation.json').read_text());assert hashlib.sha256(source.read_bytes()).hexdigest()==proof['source_files_sha256'][rel]
attempt=int(sys.argv[1]) if sys.argv[1:] else 1;assert attempt in [1,2]
out=P/('current-module-build-r'+str(attempt));out.mkdir(mode=0o700)
spec=importlib.util.spec_from_file_location('snapshot227',R.parent/'kernel227/prepare-fastrpc.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper);before=helper.snapshot()
def outputs():return {p for p in (K/'drivers/i2c/busses').iterdir() if p.is_file() and p.name.startswith(('i2c-qcom-cci','.i2c-qcom-cci'))}
names=['.config','.config.old','Module.symvers','modules.order','include/generated/compile.h','include/generated/utsversion.h','include/generated/utsrelease.h','include/generated/autoconf.h','include/config/auto.conf','include/config/auto.conf.cmd','include/config/kernel.release','drivers/i2c/busses/modules.order','drivers/i2c/busses/Module.symvers']
saved={str(p.relative_to(K)):(p.read_bytes(),stat.S_IMODE(p.stat().st_mode)) for p in outputs()|{K/n for n in names} if p.is_file()};backup=out/'before';backup.mkdir(mode=0o700)
for name,(data,mode) in saved.items():p=backup/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
env=dict(os.environ,KBUILD_BUILD_VERSION='183',PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup')
def limit():resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
ret=None;start=time.monotonic()
try:
 shutil.copyfile(source,K/rel)
 with (out/'build-private.log').open('xb') as log:
  ret=subprocess.run(['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LD=aarch64-linux-gnu-ld --no-keep-memory','W=1','-j3','drivers/i2c/busses/i2c-qcom-cci.ko'],cwd=K,env=env,stdout=log,stderr=subprocess.STDOUT,preexec_fn=limit).returncode
 if ret==0:
  shutil.copyfile(K/'drivers/i2c/busses/i2c-qcom-cci.ko',out/'i2c-qcom-cci.ko');subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(out/'i2c-qcom-cci.ko')],check=True)
finally:
 for p in outputs():
  if str(p.relative_to(K)) not in saved:p.unlink()
 for name,(data,mode) in saved.items():p=K/name;p.write_bytes(data);p.chmod(mode)
 restored=before==helper.snapshot() and all((K/n).read_bytes()==v[0] for n,v in saved.items());(out/'restoration-private.json').write_text(json.dumps(dict(exit=ret,canonical_restored=restored))+'\n');assert restored
assert ret==0,'Inspect terminal build log; original outputs restored'
diagnostics=[l for l in (out/'build-private.log').read_text().splitlines() if re.search(r'\b(warning|error):',l,re.I)];assert not diagnostics,diagnostics
module=out/'i2c-qcom-cci.ko';get=lambda field:subprocess.check_output(['modinfo','-F',field,str(module)],text=True).strip()
available={l.split()[1] for l in saved['Module.symvers'][0].decode().splitlines()};imports={l.split()[-1] for l in subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(module)],text=True).splitlines() if l.strip()};assert imports<=available,imports-available
expected=json.loads((R.parent/'kernel228/intree-build-validation.json').read_text())['vermagic'];assert get('intree')=='Y' and get('vermagic')==expected
d=dict(stage=276,attempt=attempt,build_directory=str(out),source_sha256=proof['source_files_sha256'][rel],module_sha256=hashlib.sha256(module.read_bytes()).hexdigest(),module_bytes=module.stat().st_size,intree=True,vermagic=expected,w1_diagnostics=0,imports_available=True,canonical_sources_config_and_image_restored=True,phone_unchanged=True,module_not_loaded=True,elapsed_seconds=round(time.monotonic()-start,2))
(R/'current-module-build-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
