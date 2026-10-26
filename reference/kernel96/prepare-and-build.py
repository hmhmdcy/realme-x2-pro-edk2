from pathlib import Path
import hashlib,json,shutil,subprocess
out=Path('/mnt/e/edk2-samurai-out/kernel96');prev=out.parent/'kernel95'
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel96')
kernel=Path('/home/cy122/x2pro-linux/linux');root=kernel.parent/'initramfs'
assert out.is_dir() and not (out/'Image-before').exists()
for src,name in [(kernel/'arch/arm64/boot/Image','Image-before'),(kernel/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','dtb-before'),(kernel/'usr/initramfs_data.cpio','cpio-before'),(kernel/'.config','config-before'),(root/'init','init-before'),(root/'usr/sbin/samurai-bluetooth','bluetooth-before')]:
    shutil.copyfile(src,out/name)
for name,previous in [('Image-before','Image-connectivity'),('dtb-before','dtb-connectivity'),('cpio-before','cpio-after'),('config-before','config-after')]:
    assert (out/name).read_bytes()==(prev/previous).read_bytes()
assert (out/'bluetooth-before').read_bytes()==(ref.parent/'kernel95/samurai-bluetooth').read_bytes()
for name in ('btbcm','btqca','hci_uart'):
    assert (root/f'lib/modules/samurai/{name}.ko').read_bytes()==(prev.parent/f'kernel94/{name}.ko').read_bytes()
old=(root/'init').read_text()
anchor='''# Wi-Fi firmware/NV copies and services remain in RAM; USB starts independently.
( /usr/sbin/samurai-wifi start > /run/samurai-wifi-boot.log 2>&1;
  echo "[wifi] startup exit=$?; see /run/samurai-wifi-boot.log" > /dev/kmsg ) &

# Bluetooth UART loads after Wi-Fi readiness; USB remains independent.
( /usr/sbin/samurai-bluetooth start > /run/samurai-bluetooth-boot.log 2>&1;
'''
replacement='''# Wi-Fi firmware/NV copies and services remain in RAM; USB starts independently.
mkdir -p /run/samurai-wifi
: > /run/samurai-wifi/boot-started
( /usr/sbin/samurai-wifi start > /run/samurai-wifi-boot.log 2>&1;
  wifi_result=$?
  echo "$wifi_result" > /run/samurai-wifi/boot-finished.tmp
  mv /run/samurai-wifi/boot-finished.tmp /run/samurai-wifi/boot-finished
  echo "[wifi] startup exit=$wifi_result; see /run/samurai-wifi-boot.log" > /dev/kmsg ) &

# Bluetooth follows the bounded Wi-Fi attempt, including its failure branch.
( /usr/sbin/samurai-bluetooth boot > /run/samurai-bluetooth-boot.log 2>&1;
'''
assert old.count(anchor)==1
(out/'init-after').write_text(old.replace(anchor,replacement))
subprocess.run(['sh','-n',str(out/'init-after')],check=True)
subprocess.run(['sh','-n',str(ref/'samurai-bluetooth')],check=True)
(root/'init').write_bytes((out/'init-after').read_bytes())
(root/'usr/sbin/samurai-bluetooth').write_bytes((ref/'samurai-bluetooth').read_bytes())
with (out/'build-kernel.log').open('w') as log:
    subprocess.run(['make','-j8','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','KBUILD_BUILD_VERSION=95','Image','qcom/sm8150-samurai.dtb'],cwd=kernel,stdout=log,stderr=subprocess.STDOUT,check=True)
for src,name in [(kernel/'arch/arm64/boot/Image','Image-connectivity'),(kernel/'usr/initramfs_data.cpio','cpio-after'),(kernel/'.config','config-after'),(kernel/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','dtb-connectivity')]:
    shutil.copyfile(src,out/name)
assert (out/'config-before').read_bytes()==(out/'config-after').read_bytes()
assert (out/'dtb-before').read_bytes()==(out/'dtb-connectivity').read_bytes()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report=dict(kernel_build=95,config_byte_identical=True,dtb_byte_identical=True,module_bytes_unchanged=True,image_sha256=sha(out/'Image-connectivity'),cpio_sha256=sha(out/'cpio-after'))
(out/'build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
