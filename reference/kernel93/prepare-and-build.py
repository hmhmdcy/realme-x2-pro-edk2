from pathlib import Path
import hashlib, shutil, subprocess

out=Path('/mnt/e/edk2-samurai-out/kernel93')
previous=out.parent/'kernel92'
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel93')
kernel=Path('/home/cy122/x2pro-linux/linux')
root=kernel.parent/'initramfs'
out.mkdir(mode=0o700)
for src,name in [(kernel/'arch/arm64/boot/Image','Image-before'),(kernel/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','dtb-before'),
                 (kernel/'usr/initramfs_data.cpio','cpio-before'),(kernel/'.config','config-before'),
                 (kernel/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts','dts-before'),(root/'usr/sbin/samurai-wifi','wifi-before')]:
    shutil.copyfile(src,out/name)
assert (out/'cpio-before').read_bytes()==(previous/'cpio-after').read_bytes()
assert (out/'dtb-before').read_bytes()==(previous/'dtb-connectivity').read_bytes()
wifi=(ref.parent/'kernel92/samurai-wifi').read_bytes()
assert wifi.count(b'|| return 1')==4
(root/'usr/sbin/samurai-wifi').write_bytes(wifi)
dts=kernel/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts'
before=dts.read_text()
old='compatible = "qcom,wcn3990-bt";'
assert before.count(old)==1
after=before.replace(old,old+'\n        /* Same-handset revision-21 files; ROM 0x1001 derives a missing 01 name. */\n        firmware-name = "crnv21.bin", "crbtfw21.tlv";')
dts.write_text(after)
patch=subprocess.check_output(['diff','-u','--label','a/arch/arm64/boot/dts/qcom/sm8150-samurai.dts',str(out/'dts-before'),
    '--label','b/arch/arm64/boot/dts/qcom/sm8150-samurai.dts',str(dts)],text=True) if before==after else subprocess.run(
    ['diff','-u','--label','a/arch/arm64/boot/dts/qcom/sm8150-samurai.dts',str(out/'dts-before'),'--label','b/arch/arm64/boot/dts/qcom/sm8150-samurai.dts',str(dts)],capture_output=True,text=True).stdout
(ref/'bluetooth-firmware-selection.patch').write_text(patch)
with (out/'build-kernel.log').open('w') as log:
    subprocess.run(['make','-j8','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','KBUILD_BUILD_VERSION=92','Image','qcom/sm8150-samurai.dtb'],cwd=kernel,stdout=log,stderr=subprocess.STDOUT,check=True)
for src,name in [(kernel/'arch/arm64/boot/Image','Image-connectivity'),(kernel/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','dtb-connectivity'),(kernel/'usr/initramfs_data.cpio','cpio-after')]:shutil.copyfile(src,out/name)
assert (kernel/'.config').read_bytes()==(out/'config-before').read_bytes()
print('Kernel #92 built; unchanged config, Wi-Fi startup guard and Bluetooth filename selection only')
