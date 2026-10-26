"""Build real in-tree targets temporarily, restoring all maintained inputs."""
from pathlib import Path
import hashlib,importlib.util,json,os,re,resource,shutil,stat,subprocess,time
REF=Path(__file__).resolve().parent
P=Path('/mnt/e/edk2-samurai-out/kernel232')
K=Path('/home/cy122/pmos-samurai-kernel136/kernel')
sp=importlib.util.spec_from_file_location('p227',REF.parent/'kernel227/prepare-fastrpc.py')
p=importlib.util.module_from_spec(sp);sp.loader.exec_module(p)
before=p.snapshot();assert before==json.loads((P/'kernel-before-private.json').read_text())
out=P/'module-build';out.mkdir(mode=0o700)
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
prefixes={'drivers/mfd':('qcom-pm8008','.qcom-pm8008'),
          'drivers/reset':('reset-realme-rmx1931-pm8008','.reset-realme-rmx1931-pm8008')}
def outputs():
 return {x for directory,starts in prefixes.items() for x in (K/directory).iterdir()
         if x.is_file() and x.name.startswith(starts)}
names=['drivers/reset/Makefile','.config','Module.symvers','modules.order',
       'include/generated/compile.h','include/generated/utsversion.h',
       'include/generated/autoconf.h','include/config/auto.conf',
       'include/config/auto.conf.cmd','include/config/kernel.release']
files=outputs()|{K/n for n in names if (K/n).is_file()}
saved={str(x.relative_to(K)):(x.read_bytes(),stat.S_IMODE(x.stat().st_mode)) for x in files}
backup=P/'module-build-before';backup.mkdir(mode=0o700)
for name,(data,mode) in saved.items():
 dest=backup/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
assert len(saved['Module.symvers'][0].splitlines())==16798
assert len(saved['modules.order'][0].splitlines())==772
env=dict(os.environ,KBUILD_BUILD_VERSION='183',PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup')
def limit():resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
started=time.monotonic();build_ret=None
try:
 shutil.copyfile(REF/'qcom-pm8008.c',K/'drivers/mfd/qcom-pm8008.c')
 shutil.copyfile(REF/'reset-realme-rmx1931-pm8008.c',K/'drivers/reset/reset-realme-rmx1931-pm8008.c')
 with (K/'drivers/reset/Makefile').open('ab') as f:
  f.write(b'\nobj-$(CONFIG_RESET_REALME_RMX1931_PM8008) += reset-realme-rmx1931-pm8008.o\n')
 with (out/'build-private.log').open('xb') as log:
  result=subprocess.run(['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-',
   'LD=aarch64-linux-gnu-ld --no-keep-memory','CONFIG_RESET_REALME_RMX1931_PM8008=m',
   'W=1','-j3','drivers/mfd/qcom-pm8008.ko','drivers/reset/reset-realme-rmx1931-pm8008.ko'],
   cwd=K,env=env,stdout=log,stderr=subprocess.STDOUT,preexec_fn=limit)
  build_ret=result.returncode
 if build_ret==0:
  for directory,name in [('mfd','qcom-pm8008'),('reset','reset-realme-rmx1931-pm8008')]:
   dest=out/(name+'.ko');shutil.copyfile(K/'drivers'/directory/(name+'.ko'),dest)
   subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(dest)],check=True)
finally:
 for x in outputs():
  if str(x.relative_to(K)) not in saved:x.unlink()
 for name,(data,mode) in saved.items():
  dest=K/name;dest.write_bytes(data);dest.chmod(mode)
 after=p.snapshot();assert before==after,'Maintained tree changed'
 (P/'module-build-restoration-private.json').write_text(json.dumps(dict(restored=True,build_returncode=build_ret),indent=2)+'\n')
assert build_ret==0, 'Build failed; read private build log; maintained inputs restored'
diagnostics=[s for s in (out/'build-private.log').read_text().splitlines() if re.search(r'\b(warning|error):',s,re.I)]
assert not diagnostics,diagnostics
available={s.split()[1] for s in saved['Module.symvers'][0].decode().splitlines()}
results={}
for name in ['qcom-pm8008','reset-realme-rmx1931-pm8008']:
 module=out/(name+'.ko')
 def info(field):return subprocess.check_output(['modinfo','-F',field,str(module)],text=True).strip()
 imports={s.split()[-1] for s in subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(module)],text=True).splitlines() if s.strip()}
 assert imports<=available,sorted(imports-available)
 assert info('intree')=='Y'
 assert info('vermagic')==json.loads((REF.parent/'kernel228/intree-build-validation.json').read_text())['vermagic']
 results[name]=dict(sha256=sha(module),bytes=module.stat().st_size,intree='Y',vermagic=info('vermagic'),depends=info('depends'),all_imports_available=True)
report=dict(stage=232,real_intree_targets_built=True,modules=results,w1_diagnostics=0,
 canonical_sources_config_headers_image_dtb_symbols_order_restored=True,
 no_phone_install_flash_or_reboot=True,elapsed_seconds=round(time.monotonic()-started,2))
(REF/'module-build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
