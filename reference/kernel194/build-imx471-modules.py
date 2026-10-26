from pathlib import Path
import hashlib,json,os,re,resource,shutil,subprocess
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel194');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=json.loads((ref/'imx471-source-validation.json').read_text());tests=json.loads((ref/'imx471-power-host-validation.json').read_text());assert source['checkpatch_exit']==0 and tests['source_sha256']==source['source_sha256'] and tests['asan_ubsan_passed']
assert sha(k/'drivers/media/i2c/imx471.c')==source['source_sha256']
assert all(sha(k/n)==h for n,h in source['prior16_tracked_sources'].items())
prior=json.loads((ref.parent/'kernel193/source-final-validation.json').read_text())['source_sha256'];assert all(sha(k/n)==h for n,h in prior.items())
before={n:sha(k/n) for n in ['.config','arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb']}
original={n:(k/n).read_bytes() for n in ['.config','Module.symvers','modules.order']};assert len(original['Module.symvers'].splitlines())==16793 and len(original['modules.order'].splitlines())==770
for n,b in original.items():(out/('original-'+n.replace('.','_')+'-private')).write_bytes(b)
env=dict(os.environ,KBUILD_BUILD_VERSION='183',PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup')
def limit():resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
build_log=out/'imx471-modules-build-private.log'
try:
 subprocess.run(['scripts/config','--module','VIDEO_IMX471','--disable','OF_SAMURAI_CCI_BRINGUP','--disable','OF_SAMURAI_FRONT_IDENTIFY'],cwd=k,check=True,capture_output=True)
 with (out/'imx471-olddefconfig-private.log').open('xb') as log:subprocess.run(['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','olddefconfig'],cwd=k,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 cfg=(k/'.config').read_text();assert all('CONFIG_'+n+'=m' in cfg for n in ['VIDEO_IMX471','V4L2_CCI','V4L2_CCI_I2C'])
 with build_log.open('xb') as log:subprocess.run(['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LD=aarch64-linux-gnu-ld --no-keep-memory','W=1','-j3','modules'],cwd=k,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,preexec_fn=limit)
 symbols=(k/'Module.symvers').read_bytes();(out/'new-module-symbols-private').write_bytes(symbols)
 modules=[]
 for name in ['drivers/media/v4l2-core/v4l2-cci.ko','drivers/media/i2c/imx471.ko']:
  p=k/name;dest=out/p.name;assert not dest.exists();shutil.copyfile(p,dest);subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(dest)],check=True)
  vm=subprocess.check_output(['modinfo','-F','vermagic',str(dest)],text=True).strip();assert vm==subprocess.check_output(['modinfo','-F','vermagic',str(k/'drivers/misc/fastrpc.ko')],text=True).strip()
  imports=subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(dest)],text=True);available={l.split()[1] for l in symbols.decode().splitlines()};assert all(l.split()[-1] in available for l in imports.splitlines() if l.strip())
  assert subprocess.check_output(['modinfo','-F','intree',str(dest)],text=True).strip()=='Y'
  modules.append(dict(path=name,sha256=sha(dest),bytes=dest.stat().st_size,vermagic=vm,depends=subprocess.check_output(['modinfo','-F','depends',str(dest)],text=True).strip()))
finally:
 for n,b in original.items():(k/n).write_bytes(b)
assert all(sha(k/n)==h for n,h in before.items()) and all(sha(k/n)==h for n,h in source['prior16_tracked_sources'].items())
diagnostics=re.findall(r'^.*\b(?:warning|error):.*$',build_log.read_text(),re.M);(out/'imx471-build-diagnostics-private.json').write_text(json.dumps(diagnostics,indent=2))
record=dict(stage=194,source_sha256=source['source_sha256'],modules=modules,all_imports_checked_against_combined_symbols=True,image_dtb_config_unchanged=True,prior16_tracked_sources_unchanged=True,full_symbol_table_and_order_restored=True,w1_diagnostics=len(diagnostics),hardware_deployed=False)
(ref/'imx471-modules-build-validation.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
