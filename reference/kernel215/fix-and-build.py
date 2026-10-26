from pathlib import Path
import difflib,hashlib,json,os,shutil,subprocess
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel215');kernel=Path('/home/cy122/pmos-samurai-kernel136/kernel');path=kernel/'drivers/media/i2c/imx471.c'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=(private/'imx471-before.c').read_text();assert path.read_text()==old
fragment='#define IMX471_REG_TEST_PATTERN\t\t\tCCI_REG8(0x0600)';assert old.count(fragment)==1
new=old.replace(fragment,fragment.replace('CCI_REG8','CCI_REG16'))
stock=json.loads((private.parent/'kernel213/stock-test-pattern-layout-private.json').read_text())
assert next(x for x in stock if x['id']==1056)['words'][2]==0x0601 and next(x for x in stock if x['id']==1058)['words']==[1]
upstream=private/'related-upstream/kernel/patches/0002-media-i2c-imx471-Fix-test-pattern-register-width.patch';patch=upstream.read_text()
assert '-'+fragment in patch and '+'+fragment.replace('CCI_REG8','CCI_REG16') in patch
dest=repo/'linux-port/camera/kernel';dest.mkdir(exist_ok=True)
shutil.copyfile(upstream,dest/'0001-imx471-test-pattern-width.patch')
path.write_text(new)
assert ''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/drivers/media/i2c/imx471.c',tofile='b/drivers/media/i2c/imx471.c')).count('\n-#define')==1
source=dict(stage=215,source_before_sha256=hashlib.sha256(old.encode()).hexdigest(),source_after_sha256=sha(path),only_test_pattern_width_changed=True,test_pattern_address='0x0600',old_width=8,new_width=16,own_factory_solid_color_low_byte_address='0x0601',own_factory_solid_color_low_byte_value=1,related_primary_repository='https://github.com/cschalle/mipi-fixes-x1-aura',related_primary_commit=json.loads((private/'related-upstream-source-list-private.json').read_text())['commit'],upstream_patch_commit='e8c7bce089b518b5d9076d585ebc469e9c390ff8',gain_limits_mode_registers_gpio_clock_regulators_unchanged=True,hardware_validation_pending=True)
(here/'test-pattern-source-validation.json').write_text(json.dumps(source,indent=2)+'\n')
out=private/'modules';out.mkdir(mode=0o700)
original={name:(kernel/name).read_bytes() for name in ['.config','Module.symvers','modules.order']}
preserved={name:sha(kernel/name) for name in ['arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','arch/arm64/boot/dts/qcom/sm8150-samurai.dts','drivers/media/v4l2-core/v4l2-cci.ko']}
env=dict(os.environ,KBUILD_BUILD_VERSION='183',PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup')
try:
    with (out/'build-private.log').open('xb') as log:
        subprocess.run(['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LD=aarch64-linux-gnu-ld --no-keep-memory','W=1','-j3','drivers/media/v4l2-core/v4l2-cci.ko','drivers/media/i2c/imx471.ko'],cwd=kernel,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    (out/'generated-Module.symvers-private').write_bytes((kernel/'Module.symvers').read_bytes())
    target=out/'imx471.ko';shutil.copyfile(kernel/'drivers/media/i2c/imx471.ko',target);subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(target)],check=True)
finally:
    for name,data in original.items():(kernel/name).write_bytes(data)
assert all(sha(kernel/name)==digest for name,digest in preserved.items())
available={line.split()[1] for line in original['Module.symvers'].decode().splitlines()}
imports=subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(target)],text=True);assert all(line.split()[-1] in available for line in imports.splitlines() if line.strip())
vermagic=subprocess.check_output(['modinfo','-F','vermagic',str(target)],text=True).strip();assert vermagic==json.loads((here.parent/'kernel211/imx471-module-build-validation.json').read_text())['vermagic']
assert subprocess.check_output(['modinfo','-F','intree',str(target)],text=True).strip()=='Y'
diagnostics=[line for line in (out/'build-private.log').read_text().splitlines() if 'warning:' in line.lower() or 'error:' in line.lower()];assert not diagnostics
assert subprocess.run(['git','diff','--check'],cwd=kernel,capture_output=True).returncode==0
report=dict(stage=215,source_sha256=source['source_after_sha256'],module_sha256=sha(target),module_bytes=target.stat().st_size,vermagic=vermagic,w1_diagnostics=0,all_import_names_available=True,config_symbols_order_image_board_and_cci_module_preserved=True,module_not_yet_installed=True)
(here/'imx471-module-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
