from pathlib import Path
import hashlib,json,os,shutil,subprocess
os.umask(0o077);here=Path(__file__).resolve().parent;k=Path('/home/cy122/pmos-samurai-kernel136/kernel');private=Path('/mnt/e/edk2-samurai-out/kernel211');out=private/'modules';out.mkdir(mode=0o700)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=json.loads((here/'imx471-selection-source-validation.json').read_text());assert sha(k/'drivers/media/i2c/imx471.c')==source['source_after_sha256']
original={n:(k/n).read_bytes() for n in ['.config','Module.symvers','modules.order']};assert len(original['Module.symvers'].splitlines())==16798 and len(original['modules.order'].splitlines())==772
preserve={n:sha(k/n) for n in ['arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','arch/arm64/boot/dts/qcom/sm8150-samurai.dts','drivers/media/v4l2-core/v4l2-cci.ko']}
env=dict(os.environ,KBUILD_BUILD_VERSION='183',PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup')
try:
    with (out/'build-private.log').open('xb') as log:
        subprocess.run(['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LD=aarch64-linux-gnu-ld --no-keep-memory','W=1','-j3','drivers/media/v4l2-core/v4l2-cci.ko','drivers/media/i2c/imx471.ko'],cwd=k,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    (out/'generated-Module.symvers-private').write_bytes((k/'Module.symvers').read_bytes())
    dest=out/'imx471.ko';shutil.copyfile(k/'drivers/media/i2c/imx471.ko',dest);subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(dest)],check=True)
finally:
    for n,data in original.items():(k/n).write_bytes(data)
assert {n:sha(k/n) for n in preserve}==preserve
available={line.split()[1] for line in original['Module.symvers'].decode().splitlines()}
imports=subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(dest)],text=True);assert all(l.split()[-1] in available for l in imports.splitlines() if l.strip())
vm=subprocess.check_output(['modinfo','-F','vermagic',str(dest)],text=True).strip();assert vm==json.loads((here.parent/'kernel210/camera-module-build-validation.json').read_text())['modules'][1]['vermagic']
assert subprocess.check_output(['modinfo','-F','intree',str(dest)],text=True).strip()=='Y'
diagnostics=[l for l in (out/'build-private.log').read_text().splitlines() if 'warning:' in l.lower() or 'error:' in l.lower()];assert not diagnostics,diagnostics
check=subprocess.run(['git','diff','--check'],cwd=k,capture_output=True);(out/'diff-check-private.log').write_bytes(check.stdout+check.stderr);assert check.returncode==0
report=dict(stage=211,source_sha256=source['source_after_sha256'],module_sha256=sha(dest),module_bytes=dest.stat().st_size,vermagic=vm,depends=subprocess.check_output(['modinfo','-F','depends',str(dest)],text=True).strip(),w1_diagnostics=0,all_import_names_available=True,config_symbols_order_image_board_and_cci_module_preserved=True,device_module_not_yet_installed=True)
(here/'imx471-module-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
