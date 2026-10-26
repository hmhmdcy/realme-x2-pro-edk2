from pathlib import Path
import hashlib,json,os,shutil,subprocess
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel197');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();test=json.loads((ref/'camss-lane-host-validation.json').read_text());assert test['source_sha256']==sha(k/'drivers/media/platform/qcom/camss/camss.c') and test['asan_ubsan_passed']
original={n:(k/n).read_bytes() for n in ['.config','Module.symvers','modules.order']};base={n:sha(k/n) for n in ['arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb']};assert len(original['Module.symvers'].splitlines())==16793 and len(original['modules.order'].splitlines())==770
env=dict(os.environ,KBUILD_BUILD_VERSION='183',PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup');assert 'CONFIG_VIDEO_QCOM_CAMSS=m' in original['.config'].decode()
all_symbols=(out.parent/'kernel194/new-module-symbols-private').read_text();base_symbols={s.split()[1] for s in original['Module.symvers'].decode().splitlines()};rows=[s for s in all_symbols.splitlines() if 'drivers/media/common/videobuf2/' in s];assert any('vb2_queue_init' in s for s in rows);extra=out/'camss-extra-symbols-private.symvers';extra.write_text('\n'.join(rows)+'\n')
try:
 with (out/'camss-olddefconfig-r6-private.log').open('xb') as log:subprocess.run(['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','olddefconfig'],cwd=k,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 with (out/'camss-module-build-r6-private.log').open('xb') as log:subprocess.run(['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LD=aarch64-linux-gnu-ld --no-keep-memory','W=1','-j3','drivers/media/common/videobuf2/videobuf2-common.ko','drivers/media/common/videobuf2/videobuf2-memops.ko','drivers/media/common/videobuf2/videobuf2-v4l2.ko','drivers/media/common/videobuf2/videobuf2-dma-sg.ko','drivers/media/platform/qcom/camss/qcom-camss.ko'],cwd=k,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 dest=out/'qcom-camss-diagnostic.ko';assert not dest.exists();shutil.copyfile(k/'drivers/media/platform/qcom/camss/qcom-camss.ko',dest);subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(dest)],check=True)
finally:
 for n,b in original.items():(k/n).write_bytes(b)
assert all(sha(k/n)==v for n,v in base.items());vm=subprocess.check_output(['modinfo','-F','vermagic',str(dest)],text=True).strip();assert vm==json.loads((ref.parent/'kernel195/pmic-module-build-validation.json').read_text())['vermagic'];assert subprocess.check_output(['modinfo','-F','intree',str(dest)],text=True).strip()=='Y'
diagnostics=[s for s in (out/'camss-module-build-r6-private.log').read_text().splitlines() if 'warning:' in s or 'error:' in s];assert not diagnostics,diagnostics
r=dict(stage=197,source_sha256=test['source_sha256'],csid_diagnostic_source_sha256=sha(k/"drivers/media/platform/qcom/camss/camss-csid-gen2.c"),module_sha256=sha(dest),module_bytes=dest.stat().st_size,vermagic=vm,w1_diagnostics=0,base_image_dtb_config_symbols_order_unchanged=True,persistent_modules_unchanged=True);(ref/'camss-diagnostic-module-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))



