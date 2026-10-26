from pathlib import Path
import hashlib,json,shutil,subprocess
out=Path('/mnt/e/edk2-samurai-out/kernel95');prev=out.parent/'kernel94'
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel95')
kernel=Path('/home/cy122/x2pro-linux/linux');root=kernel.parent/'initramfs'
assert not out.exists();out.mkdir(mode=0o700)
for src,name in [(kernel/'arch/arm64/boot/Image','Image-before'),(kernel/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','dtb-before'),(kernel/'usr/initramfs_data.cpio','cpio-before'),(kernel/'.config','config-before')]:shutil.copyfile(src,out/name)
for name,previous in [('Image-before','Image-connectivity'),('dtb-before','dtb-connectivity'),('cpio-before','cpio-after'),('config-before','config-after')]:
    assert (out/name).read_bytes()==(prev/previous).read_bytes()
old=root/'usr/sbin/samurai-bluetooth';before=old.read_bytes();new=(ref/'samurai-bluetooth').read_bytes()
assert before.replace(b'/sbin/insmod',b'/bin/insmod')==new
assert new.count(b'/bin/insmod')==3
for name in ('btbcm','btqca','hci_uart'):
    assert (root/f'lib/modules/samurai/{name}.ko').read_bytes()==(prev/f'{name}.ko').read_bytes()
old.write_bytes(new)
with (out/'build-kernel.log').open('w') as log:subprocess.run(['make','-j8','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','KBUILD_BUILD_VERSION=94','Image','qcom/sm8150-samurai.dtb'],cwd=kernel,stdout=log,stderr=subprocess.STDOUT,check=True)
for src,name in [(kernel/'arch/arm64/boot/Image','Image-connectivity'),(kernel/'usr/initramfs_data.cpio','cpio-after'),(kernel/'.config','config-after'),(kernel/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','dtb-connectivity')]:shutil.copyfile(src,out/name)
assert (out/'config-before').read_bytes()==(out/'config-after').read_bytes()
assert (out/'dtb-before').read_bytes()==(out/'dtb-connectivity').read_bytes()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report=dict(kernel_build=94,config_byte_identical=True,dtb_byte_identical=True,module_bytes_unchanged=True,image_sha256=sha(out/'Image-connectivity'),cpio_sha256=sha(out/'cpio-after'))
(out/'build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
