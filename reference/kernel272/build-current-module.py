"""Build Image183-compatible GW1/CCI modules and restore canonical tree bytes."""
from pathlib import Path
import hashlib,importlib.util,json,os,re,resource,shutil,stat,subprocess,time
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel272')
K=Path('/home/cy122/pmos-samurai-kernel136/kernel');W=Path('/home/cy122/x2pro-linux/camera270-kernel')
out=P/'current-module-build-r1';out.mkdir(mode=0o700)
spec=importlib.util.spec_from_file_location('snapshot227',R.parent/'kernel227/prepare-fastrpc.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper);before=helper.snapshot()
mapping={'s5kgw1.c':'drivers/media/i2c/s5kgw1.c','s5kgw1-tables.h':'drivers/media/i2c/s5kgw1-tables.h'}
assert all(not (K/n).exists() for n in mapping.values())
prefixes={'drivers/media/i2c':('s5kgw1','.s5kgw1'),'drivers/media/v4l2-core':('v4l2-cci','.v4l2-cci')}
def outputs():return {p for directory,starts in prefixes.items() for p in (K/directory).iterdir() if p.is_file() and p.name.startswith(starts)}
names=['.config','.config.old','Module.symvers','modules.order','include/generated/compile.h','include/generated/utsversion.h',
 'include/generated/utsrelease.h','include/generated/autoconf.h','include/config/auto.conf','include/config/auto.conf.cmd','include/config/kernel.release',
 'drivers/media/i2c/Kconfig','drivers/media/i2c/Makefile','drivers/media/i2c/modules.order','drivers/media/i2c/Module.symvers',
 'drivers/media/v4l2-core/modules.order','drivers/media/v4l2-core/Module.symvers']
saved={str(p.relative_to(K)):(p.read_bytes(),stat.S_IMODE(p.stat().st_mode)) for p in outputs()|{K/n for n in names} if p.is_file()}
backup=out/'before';backup.mkdir(mode=0o700)
for name,(data,mode) in saved.items():
 p=backup/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
env=dict(os.environ,KBUILD_BUILD_VERSION='183',PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup')
def limit():resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
ret=None;start=time.monotonic();targets=['drivers/media/v4l2-core/v4l2-cci.ko','drivers/media/i2c/s5kgw1.ko'];extra_exports=set()
try:
 for name,dest in mapping.items():shutil.copyfile(R/name,K/dest)
 with (K/'drivers/media/i2c/Makefile').open('a') as f:f.write('\nobj-$(CONFIG_VIDEO_S5KGW1) += s5kgw1.o\n')
 text=(W/'drivers/media/i2c/Kconfig').read_text();entry=text[text.index('config VIDEO_S5KGW1\n'):text.index('config VIDEO_S5K3M5\n')]
 with (K/'drivers/media/i2c/Kconfig').open('a') as f:f.write('\n'+entry)
 with (out/'build-private.log').open('xb') as log:
  ret=subprocess.run(['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LD=aarch64-linux-gnu-ld --no-keep-memory',
   'CONFIG_VIDEO_S5KGW1=m','CONFIG_V4L2_CCI=m','CONFIG_V4L2_CCI_I2C=m','W=1','-j3',*targets],cwd=K,env=env,stdout=log,stderr=subprocess.STDOUT,preexec_fn=limit).returncode
 if ret==0:
  for name in targets:
   dest=out/Path(name).name;shutil.copyfile(K/name,dest)
   subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(dest)],check=True)
  extra_exports={l.split()[1] for l in (K/'Module.symvers').read_text().splitlines() if l.strip()}
finally:
 for p in outputs():
  if str(p.relative_to(K)) not in saved:p.unlink()
 for name,(data,mode) in saved.items():
  p=K/name;p.write_bytes(data);p.chmod(mode)
 restored=before==helper.snapshot()
 (out/'restoration-private.json').write_text(json.dumps(dict(exit=ret,canonical_restored=restored))+'\n')
 assert restored,'Inspect canonical changes; no phone changes have occurred'
assert ret==0,'Compile failed; canonical restored; inspect this log'
diagnostics=[l for l in (out/'build-private.log').read_text().splitlines() if re.search(r'\b(warning|error):',l,re.I)]
assert not diagnostics,diagnostics
available={l.split()[1] for l in saved['Module.symvers'][0].decode().splitlines()}
expected=json.loads((R.parent/'kernel228/intree-build-validation.json').read_text())['vermagic']
modules={}
for name in targets:
 mod=out/Path(name).name
 get=lambda key:subprocess.check_output(['modinfo','-F',key,str(mod)],text=True).strip()
 imports={l.split()[-1] for l in subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(mod)],text=True).splitlines() if l.strip()}
 assert imports<=available|extra_exports,(mod.name,imports-available-extra_exports)
 assert get('intree')=='Y' and get('vermagic')==expected
 modules[mod.name]=dict(sha256=hashlib.sha256(mod.read_bytes()).hexdigest(),bytes=mod.stat().st_size,depends=get('depends'))
assert modules['v4l2-cci.ko']['sha256']=='f9c9272ac6f19712fee621b4c583f517112b6ed90324e21600d5c0c23b74a03d'
report=dict(stage=272,modules=modules,intree=True,vermagic=expected,imports_available=True,w1_diagnostics=0,
 source_sha256=hashlib.sha256((R/'s5kgw1.c').read_bytes()).hexdigest(),
 canonical_sources_config_and_image_restored=True,cci_identical_to_current=True,
 elapsed_seconds=round(time.monotonic()-start,2),phone_unchanged=True,module_not_yet_loaded=True)
(R/'current-module-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
