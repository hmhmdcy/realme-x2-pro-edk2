from pathlib import Path
import hashlib,json,os,shutil,subprocess
ref=Path(__file__).resolve().parent;k=Path('/home/cy122/pmos-samurai-kernel136/kernel');out=Path('/mnt/e/edk2-samurai-out/kernel200');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
name='samurai-vio-phandle';src=k/('drivers/of/'+name+'.c')
if src.exists():
 backup=out/'vio-helper-before200-private.c';assert not backup.exists();shutil.copyfile(src,backup)
shutil.copyfile(ref/(name+'.c'),src)
make=k/'drivers/of/Makefile';cfg=k/'drivers/of/Kconfig'
if 'CONFIG_OF_SAMURAI_VIO_PHANDLE' not in make.read_text():
 with make.open('a') as p:p.write('obj-$(CONFIG_OF_SAMURAI_VIO_PHANDLE) += samurai-vio-phandle.o\n')
if 'config OF_SAMURAI_VIO_PHANDLE' not in cfg.read_text():
 with cfg.open('a') as p:p.write('''
config OF_SAMURAI_VIO_PHANDLE
	tristate "Temporary realme X2 Pro VIO phandle fixture"
	depends on OF_DYNAMIC && ARCH_QCOM && MODULES && REGULATOR
	help
	  Temporarily add a phandle to the existing inactive camera VIO
	  regulator node through reversible OF changesets. Verify an exact
	  OF supply lookup without enabling power. Development only; leave
	  disabled and use static device tree references for normal builds.
''')
patch=subprocess.run(['git','diff','--no-index','--','/dev/null',str(src)],capture_output=True,text=True).stdout.replace('b'+str(k)+'/', 'b/').replace('a'+str(k)+'/', 'a/');(ref/'samurai-vio-phandle.patch').write_text(patch)
c=subprocess.run(['perl',str(k/'scripts/checkpatch.pl'),'--no-tree','--strict','--ignore','FILE_PATH_CHANGES','-'],input=patch,capture_output=True,text=True);(out/'vio-checkpatch-private.log').write_text(c.stdout+c.stderr);assert c.returncode==0,c.stdout
original={n:(k/n).read_bytes() for n in ['.config','Module.symvers','modules.order']};image=sha(k/'arch/arm64/boot/Image');dtb=sha(k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb')
env=dict(os.environ,KBUILD_BUILD_VERSION='183',PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup')
try:
 (k/'.config').write_bytes(original['.config']+''.join('\n# CONFIG_OF_SAMURAI_'+s+' is not set\n' for s in ['CCI_BRINGUP','FRONT_IDENTIFY','PMIC_FIXTURE','VIO_PHANDLE']).encode())
 with (out/'vio-module-build-private.log').open('xb') as log:subprocess.run(['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LD=aarch64-linux-gnu-ld --no-keep-memory','CONFIG_OF_SAMURAI_VIO_PHANDLE=m','W=1','-j3','drivers/of/'+name+'.ko'],cwd=k,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
finally:
 for n,b in original.items():(k/n).write_bytes(b)
dest=out/(name+'.ko');assert not dest.exists();shutil.copyfile(k/('drivers/of/'+name+'.ko'),dest);subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(dest)],check=True)
vm=subprocess.check_output(['modinfo','-F','vermagic',str(dest)],text=True).strip();assert vm==json.loads((ref.parent/'kernel195/pmic-module-build-validation.json').read_text())['vermagic']
available={s.split()[1] for s in original['Module.symvers'].decode().splitlines()};imports=subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(dest)],text=True);assert all(l.split()[-1] in available for l in imports.splitlines() if l.strip())
assert subprocess.check_output(['modinfo','-F','intree',str(dest)],text=True).strip()=='Y'
assert sha(k/'arch/arm64/boot/Image')==image and sha(k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb')==dtb
diagnostics=[s for s in (out/'vio-module-build-private.log').read_text().splitlines() if 'warning:' in s or 'error:' in s];assert not diagnostics,diagnostics
r=dict(stage=200,source_sha256=sha(src),module_sha256=sha(dest),module_bytes=dest.stat().st_size,vermagic=vm,checkpatch_exit=0,w1_diagnostics=0,base_image_dtb_config_symbols_order_unchanged=True,all_imports_checked_against_base_symbols=True,built_via_in_tree_kbuild=True,manual_intree_metadata=False,runtime_loaded=False,regulator_enable_or_voltage_writes=False,rpmh_unknown_state_accepted_without_power_write=True)
(ref/'vio-helper-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
