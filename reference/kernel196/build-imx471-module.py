from pathlib import Path
import hashlib,json,os,shutil,subprocess
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel196');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=json.loads((ref/'imx471-source-validation.json').read_text());test=json.loads((ref/'imx471-power-host-validation.json').read_text());assert source['source_sha256']==test['source_sha256']==sha(k/'drivers/media/i2c/imx471.c') and test['asan_ubsan_passed']
original={n:(k/n).read_bytes() for n in ['.config','Module.symvers','modules.order']};symbols=(out.parent/'kernel194/new-module-symbols-private').read_bytes();assert len(original['Module.symvers'].splitlines())==16793 and len(original['modules.order'].splitlines())==770
base={n:sha(k/n) for n in ['arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb']};env=dict(os.environ,KBUILD_BUILD_VERSION='183',PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup')
cci_symbols=[s for s in symbols.decode().splitlines() if 'drivers/media/v4l2-core/v4l2-cci' in s];assert len(cci_symbols)>=4;extra=out/'v4l2-cci-symbols-private.symvers';extra.write_text('\n'.join(cci_symbols)+'\n')
try:
 subprocess.run(['scripts/config','--module','VIDEO_IMX471'],cwd=k,check=True,capture_output=True)
 with (out/'imx471-olddefconfig-r3-private.log').open('xb') as log:subprocess.run(['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','olddefconfig'],cwd=k,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 assert all('CONFIG_'+n+'=m' in (k/'.config').read_text() for n in ['VIDEO_IMX471','V4L2_CCI','V4L2_CCI_I2C'])
 with (out/'imx471-module-build-r3-private.log').open('xb') as log:subprocess.run(['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LD=aarch64-linux-gnu-ld --no-keep-memory','W=1','-j3','drivers/media/v4l2-core/v4l2-cci.ko','drivers/media/i2c/imx471.ko'],cwd=k,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 dest=out/'imx471.ko';assert not dest.exists();shutil.copyfile(k/'drivers/media/i2c/imx471.ko',dest);subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(dest)],check=True)
 cci=out/'v4l2-cci.ko';assert not cci.exists();shutil.copyfile(k/'drivers/media/v4l2-core/v4l2-cci.ko',cci);subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(cci)],check=True)
finally:
 for n,b in original.items():(k/n).write_bytes(b)
assert all(sha(k/n)==h for n,h in base.items());available={s.split()[1] for s in symbols.decode().splitlines()};imports=subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(dest)],text=True);assert all(l.split()[-1] in available for l in imports.splitlines() if l.strip());vm=subprocess.check_output(['modinfo','-F','vermagic',str(dest)],text=True).strip();assert vm==json.loads((ref.parent/'kernel195/pmic-module-build-validation.json').read_text())['vermagic']
assert subprocess.check_output(['modinfo','-F','intree',str(dest)],text=True).strip()=='Y';diagnostics=[s for s in (out/'imx471-module-build-r3-private.log').read_text().splitlines() if 'warning:' in s or 'error:' in s];assert not diagnostics,diagnostics
r=dict(stage=196,source_sha256=source['source_sha256'],module_sha256=sha(dest),module_bytes=dest.stat().st_size,cci_module_sha256=sha(cci),vermagic=vm,depends=subprocess.check_output(['modinfo','-F','depends',str(dest)],text=True).strip(),all_imports_checked_against_combined_symbols=True,base_image_dtb_config_symbols_order_unchanged=True,w1_diagnostics=0,first_two_single_module_modpost_attempts_missing_cci_exports=True,combined_two_module_targets_resolved_exports=True,hardware_deployed=False);(ref/'imx471-module-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
