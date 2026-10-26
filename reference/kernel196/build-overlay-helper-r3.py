from pathlib import Path
import hashlib,json,os,shutil,subprocess
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel196');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();name='samurai-front-overlay';src=k/('drivers/of/'+name+'.c');shutil.copyfile(src,out/'overlay-second-source-private.c');shutil.copyfile(k/('drivers/of/'+name+'.ko'),out/'overlay-second-build-private.ko');shutil.copyfile(ref/(name+'.c'),src)
if 'CONFIG_OF_SAMURAI_FRONT_OVERLAY' not in (k/'drivers/of/Makefile').read_text():
 with (k/'drivers/of/Makefile').open('a') as p:p.write('obj-$(CONFIG_OF_SAMURAI_FRONT_OVERLAY) += samurai-front-overlay.o\n')
if 'config OF_SAMURAI_FRONT_OVERLAY' not in (k/'drivers/of/Kconfig').read_text():
 with (k/'drivers/of/Kconfig').open('a') as p:p.write('''
config OF_SAMURAI_FRONT_OVERLAY
	tristate "Temporary realme X2 Pro front sensor overlay"
	depends on OF_OVERLAY && ARCH_QCOM && MODULES
	help
	  Load and reversibly apply a development front-camera resource
	  overlay. The normal IMX471 driver performs all sensor operations.
	  Restore the sleep pin states when removing the overlay.
	  Leave disabled for normal builds and use the static board tree.
''')
patch=subprocess.run(['git','diff','--no-index','--','/dev/null',str(src)],capture_output=True,text=True).stdout.replace('b'+str(k)+'/', 'b/').replace('a'+str(k)+'/', 'a/');(ref/'samurai-front-overlay.patch').write_text(patch)
c=subprocess.run(['perl',str(k/'scripts/checkpatch.pl'),'--no-tree','--strict','--ignore','FILE_PATH_CHANGES','-'],input=patch,capture_output=True,text=True);(out/'overlay-checkpatch-private.log').write_text(c.stdout+c.stderr);assert c.returncode==0,c.stdout
original={n:(k/n).read_bytes() for n in ['.config','Module.symvers','modules.order']};base={n:sha(k/n) for n in ['arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb']};env=dict(os.environ,KBUILD_BUILD_VERSION='183',PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup')
try:
 (k/'.config').write_bytes(original['.config']+''.join('\n# CONFIG_OF_SAMURAI_'+s+' is not set\n' for s in ['CCI_BRINGUP','FRONT_IDENTIFY','PMIC_FIXTURE','VIO_PHANDLE','FRONT_OVERLAY']).encode())
 with (out/'overlay-module-build-r3-private.log').open('xb') as log:subprocess.run(['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LD=aarch64-linux-gnu-ld --no-keep-memory','CONFIG_OF_SAMURAI_FRONT_OVERLAY=m','W=1','-j3','drivers/of/'+name+'.ko'],cwd=k,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
finally:
 for n,b in original.items():(k/n).write_bytes(b)
dest=out/(name+'.ko');shutil.copyfile(dest,out/'overlay-second-stripped-private.ko');shutil.copyfile(k/('drivers/of/'+name+'.ko'),dest);subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(dest)],check=True);vm=subprocess.check_output(['modinfo','-F','vermagic',str(dest)],text=True).strip();assert vm==json.loads((ref.parent/'kernel195/pmic-module-build-validation.json').read_text())['vermagic'];available={s.split()[1] for s in original['Module.symvers'].decode().splitlines()};imports=subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(dest)],text=True);assert all(l.split()[-1] in available for l in imports.splitlines() if l.strip())
assert all(sha(k/n)==h for n,h in base.items()) and subprocess.check_output(['modinfo','-F','intree',str(dest)],text=True).strip()=='Y';diagnostics=[s for s in (out/'overlay-module-build-r3-private.log').read_text().splitlines() if 'warning:' in s or 'error:' in s];assert not diagnostics,diagnostics
r=dict(stage=196,source_sha256=sha(src),module_sha256=sha(dest),module_bytes=dest.stat().st_size,vermagic=vm,checkpatch_exit=0,w1_diagnostics=0,base_image_dtb_config_symbols_order_unchanged=True,all_imports_checked_against_base_symbols=True,manual_intree_metadata=False,hardware_loaded=False);(ref/'overlay-helper-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
