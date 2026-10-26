from pathlib import Path
import hashlib,json,os,shutil,subprocess
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel195');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
v=json.loads((ref/'pmic-address-source-validation.json').read_text());t=json.loads((ref/'pmic-address-host-validation.json').read_text())
assert v['checkpatch_exit']==0 and t['asan_ubsan_passed'] and sha(k/'drivers/mfd/qcom-pm8008.c')==v['source_sha256']==t['source_sha256']
original={n:(k/n).read_bytes() for n in ['.config','Module.symvers','modules.order']};assert len(original['Module.symvers'].splitlines())==16793 and len(original['modules.order'].splitlines())==770
image=sha(k/'arch/arm64/boot/Image');dtb=sha(k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb');assert image=='bfa72dd920c8376ceefc458fe7202a73ddb364b6727556471d70c8d0e7ade469'
old=k/'drivers/mfd/qcom-pm8008.ko';backup=out/'qcom-pm8008-before-build-private.ko'
if backup.exists():assert sha(old)==sha(backup)
else:shutil.copyfile(old,backup)
env=dict(os.environ,KBUILD_BUILD_VERSION='183',PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup')
try:
 with (out/'pmic-olddefconfig-r2-private.log').open('xb') as log:subprocess.run(['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','olddefconfig'],cwd=k,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 generated=(k/'.config').read_bytes();(out/'pmic-generated-config-private').write_bytes(generated)
 delta=set(generated.decode().splitlines())^set(original['.config'].decode().splitlines())
 assert delta=={'# CONFIG_OF_SAMURAI_CCI_BRINGUP is not set','# CONFIG_OF_SAMURAI_FRONT_IDENTIFY is not set','# CONFIG_OF_SAMURAI_PMIC_FIXTURE is not set'},delta
 with (out/'pmic-module-build-private.log').open('xb') as log:subprocess.run(['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LD=aarch64-linux-gnu-ld --no-keep-memory','W=1','-j3','drivers/mfd/qcom-pm8008.ko'],cwd=k,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 dest=out/'qcom-pm8008.ko';assert not dest.exists();shutil.copyfile(old,dest);subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(dest)],check=True)
 vm=subprocess.check_output(['modinfo','-F','vermagic',str(dest)],text=True).strip();assert vm==subprocess.check_output(['modinfo','-F','vermagic',str(backup)],text=True).strip()
 imports=subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(dest)],text=True);available={s.split()[1] for s in original['Module.symvers'].decode().splitlines()};assert all(l.split()[-1] in available for l in imports.splitlines() if l.strip())
 assert subprocess.check_output(['modinfo','-F','intree',str(dest)],text=True).strip()=='Y'
finally:
 for n,b in original.items():(k/n).write_bytes(b)
assert sha(k/'arch/arm64/boot/Image')==image and sha(k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb')==dtb
diagnostics=[s for s in (out/'pmic-module-build-private.log').read_text().splitlines() if 'warning:' in s or 'error:' in s];assert not diagnostics,diagnostics
r=dict(stage=195,source_sha256=v['source_sha256'],module_sha256=sha(dest),module_bytes=dest.stat().st_size,vermagic=vm,depends=subprocess.check_output(['modinfo','-F','depends',str(dest)],text=True).strip(),all_imports_checked_against_base_symbols=True,base_image_dtb_config_symbols_order_unchanged=True,three_new_default_disabled_config_comments_only=True,w1_diagnostics=0,hardware_deployed=False)
(ref/'pmic-module-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
