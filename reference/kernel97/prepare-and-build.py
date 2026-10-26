from pathlib import Path
import hashlib, json, shutil, subprocess

out = Path('/mnt/e/edk2-samurai-out/kernel97')
prev = out.parent / 'kernel96'
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel97')
kernel = Path('/home/cy122/x2pro-linux/linux')
root = kernel.parent / 'initramfs'
assert json.loads((out / 'runtime-validation.json').read_text())['runtime_address_lifecycle_pass']
assert not (out / 'Image-before').exists()
for src, name, expected in (
    (kernel / 'arch/arm64/boot/Image', 'Image-before', prev / 'Image-connectivity'),
    (kernel / 'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb', 'dtb-before', prev / 'dtb-connectivity'),
    (kernel / 'usr/initramfs_data.cpio', 'cpio-before', prev / 'cpio-after'),
    (kernel / '.config', 'config-before', prev / 'config-after'),
    (root / 'init', 'init-before', prev / 'init-after'),
    (root / 'usr/sbin/samurai-bluetooth', 'bluetooth-before', ref.parent / 'kernel96/samurai-bluetooth'),
):
    assert src.read_bytes() == expected.read_bytes(), name
    shutil.copyfile(src, out / name)
shutil.copyfile(root / 'usr/sbin/samurai-wifi', out / 'wifi-before')
source_before = subprocess.check_output(['git', 'diff', '--binary', 'HEAD'], cwd=kernel)
(out / 'kernel-source-before.patch').write_bytes(source_before)
wifi = (root / 'usr/sbin/samurai-wifi').read_text()
anchor = '    test -e /sys/class/net/wlan0\n    ip link set wlan0 up\n'
assert wifi.count(anchor) == 1
wifi = wifi.replace(anchor, '    test -e /sys/class/net/wlan0\n    /usr/sbin/samurai-radio-address wlan\n    ip link set wlan0 up\n')
(ref / 'samurai-wifi').write_text(wifi)
for name in ('samurai-wifi', 'samurai-bluetooth', 'samurai-radio-address'):
    subprocess.run(['sh', '-n', str(ref / name)], check=True)
    target = root / 'usr/sbin' / name
    if name == 'samurai-radio-address':
        assert not target.exists()
    target.write_bytes((ref / name).read_bytes())
    target.chmod(0o755)
for name in ('samurai-dms-mac-read', 'samurai-bt-address'):
    target = root / 'usr/sbin' / name
    assert not target.exists()
    target.write_bytes((out / name).read_bytes())
    target.chmod(0o755)
with (out / 'build-kernel.log').open('x') as log:
    subprocess.run(['make', '-j8', 'ARCH=arm64', 'CROSS_COMPILE=aarch64-linux-gnu-', 'KBUILD_BUILD_VERSION=96', 'Image', 'qcom/sm8150-samurai.dtb'], cwd=kernel, stdout=log, stderr=subprocess.STDOUT, check=True)
for src, name in (
    (kernel / 'arch/arm64/boot/Image', 'Image-connectivity'),
    (kernel / 'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb', 'dtb-connectivity'),
    (kernel / 'usr/initramfs_data.cpio', 'cpio-after'),
    (kernel / '.config', 'config-after'),
):
    shutil.copyfile(src, out / name)
assert source_before == subprocess.check_output(['git', 'diff', '--binary', 'HEAD'], cwd=kernel)
assert (out / 'config-before').read_bytes() == (out / 'config-after').read_bytes()
assert (out / 'dtb-before').read_bytes() == (out / 'dtb-connectivity').read_bytes()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
report = dict(kernel_build=96, kernel_source_unchanged=True, init_unchanged=True,
              config_byte_identical=True, dtb_byte_identical=True,
              image_sha256=sha(out / 'Image-connectivity'), cpio_sha256=sha(out / 'cpio-after'))
(out / 'build-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
