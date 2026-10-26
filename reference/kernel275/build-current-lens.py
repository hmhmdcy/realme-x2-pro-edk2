"""Build the standard lens module against the deployed Image183 and restore canonical outputs."""
from pathlib import Path
import hashlib,importlib.util,json,os,re,resource,shutil,stat,subprocess,time
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE;K=Path('/home/cy122/pmos-samurai-kernel136/kernel');W=Path('/home/cy122/x2pro-linux/camera270-kernel')
source=R.parent/'kernel274/lc898219xi.c';proof=json.loads((R.parent/'kernel274/lens-candidate-source-validation.json').read_text());assert hashlib.sha256(source.read_bytes()).hexdigest()==proof['source_sha256']
assert (W/'drivers/media/i2c/lc898219xi.c').read_bytes()==source.read_bytes()
out=P/'current-module-build-r1';out.mkdir(mode=0o700)
spec=importlib.util.spec_from_file_location('snapshot227',R.parent/'kernel227/prepare-fastrpc.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper);before=helper.snapshot()
assert not (K/'drivers/media/i2c/lc898219xi.c').exists()
def outputs():return {p for p in (K/'drivers/media/i2c').iterdir() if p.is_file() and p.name.startswith(('lc898219xi','.lc898219xi'))}
names=['.config','.config.old','Module.symvers','modules.order','include/generated/compile.h','include/generated/utsversion.h','include/generated/utsrelease.h','include/generated/autoconf.h','include/config/auto.conf','include/config/auto.conf.cmd','include/config/kernel.release','drivers/media/i2c/Kconfig','drivers/media/i2c/Makefile','drivers/media/i2c/modules.order','drivers/media/i2c/Module.symvers']
saved={str(p.relative_to(K)):(p.read_bytes(),stat.S_IMODE(p.stat().st_mode)) for p in outputs()|{K/n for n in names} if p.is_file()};backup=out/'before';backup.mkdir(mode=0o700)
for name,(data,mode) in saved.items():p=backup/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
env=dict(os.environ,KBUILD_BUILD_VERSION='183',PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup')
def limit():resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
ret=None;start=time.monotonic()
try:
 shutil.copyfile(source,K/'drivers/media/i2c/lc898219xi.c')
 with (K/'drivers/media/i2c/Makefile').open('a') as f:f.write('\nobj-$(CONFIG_VIDEO_LC898219XI) += lc898219xi.o\n')
 text=(W/'drivers/media/i2c/Kconfig').read_text();entry=text[text.index('config VIDEO_LC898219XI\n'):text.index('config VIDEO_S5KGW1\n')]
 with (K/'drivers/media/i2c/Kconfig').open('a') as f:f.write('\n'+entry)
 with (out/'build-private.log').open('xb') as log:
  ret=subprocess.run(['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LD=aarch64-linux-gnu-ld --no-keep-memory','CONFIG_VIDEO_LC898219XI=m','W=1','-j3','drivers/media/i2c/lc898219xi.ko'],cwd=K,env=env,stdout=log,stderr=subprocess.STDOUT,preexec_fn=limit).returncode
 if ret==0:
  shutil.copyfile(K/'drivers/media/i2c/lc898219xi.ko',out/'lc898219xi.ko');subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(out/'lc898219xi.ko')],check=True)
finally:
 for p in outputs():
  if str(p.relative_to(K)) not in saved:p.unlink()
 for name,(data,mode) in saved.items():p=K/name;p.write_bytes(data);p.chmod(mode)
 restored=before==helper.snapshot();(out/'restoration-private.json').write_text(json.dumps(dict(exit=ret,canonical_restored=restored))+'\n');assert restored,'Inspect canonical changes before further work'
assert ret==0,'Compile failed; original outputs restored; inspect retained log'
diagnostics=[l for l in (out/'build-private.log').read_text().splitlines() if re.search(r'\b(warning|error):',l,re.I)];assert not diagnostics,diagnostics
module=out/'lc898219xi.ko';get=lambda field:subprocess.check_output(['modinfo','-F',field,str(module)],text=True).strip()
available={l.split()[1] for l in saved['Module.symvers'][0].decode().splitlines()};imports={l.split()[-1] for l in subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(module)],text=True).splitlines() if l.strip()}
assert imports<=available,imports-available
expected=json.loads((R.parent/'kernel228/intree-build-validation.json').read_text())['vermagic'];assert get('intree')=='Y' and get('vermagic')==expected
report=dict(stage=275,source_sha256=proof['source_sha256'],module_sha256=hashlib.sha256(module.read_bytes()).hexdigest(),module_bytes=module.stat().st_size,intree=True,vermagic=expected,depends=get('depends'),imports_available=True,w1_diagnostics=0,canonical_sources_config_and_image_restored=True,phone_unchanged=True,module_not_loaded=True,elapsed_seconds=round(time.monotonic()-start,2))
(R/'current-module-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
