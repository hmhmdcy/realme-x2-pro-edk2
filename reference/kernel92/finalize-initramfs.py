from pathlib import Path
import hashlib, json, shutil, subprocess

out = Path('/mnt/e/edk2-samurai-out/kernel92')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel92')
initramfs = Path('/home/cy122/x2pro-linux/initramfs')
kernel = initramfs.parent/'linux'
hook = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel91/udhcpc-wlan.sh').read_text().replace('/tmp/k91-', '/run/samurai-wifi/')
(ref/'udhcpc-wlan.sh').write_text(hook)
target = initramfs/'usr/sbin/samurai-udhcpc-wlan'
assert not target.exists()
target.write_text(hook); target.chmod(0o755)
for name in ('Image-connectivity','cpio-after'):
    shutil.copyfile(out/name, out/(name+'-initial'))
with (out/'finalize-build.log').open('w') as log:
    subprocess.run(['make','-j8','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','KBUILD_BUILD_VERSION=91','Image','qcom/sm8150-samurai.dtb'],cwd=kernel,stdout=log,stderr=subprocess.STDOUT,check=True)
for source,name in [('arch/arm64/boot/Image','Image-connectivity'),('usr/initramfs_data.cpio','cpio-after')]:
    shutil.copyfile(kernel/source,out/name)
after = {str(p.relative_to(initramfs)):{'mode':p.lstat().st_mode,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in initramfs.rglob('*') if p.is_file() and not p.is_symlink()}
(out/'initramfs-after.json').write_text(json.dumps(after,indent=2)+'\n')
with (out/'build-hashes.txt').open('w') as log:
    subprocess.run(['sha256sum',str(out/'Image-connectivity'),str(out/'dtb-connectivity'),str(out/'cpio-after')],stdout=log,check=True)
print((out/'build-hashes.txt').read_text())
