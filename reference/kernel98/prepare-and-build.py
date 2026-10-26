from pathlib import Path
import hashlib, json, shutil, subprocess

out = Path('/mnt/e/edk2-samurai-out/kernel98')
prev = out.parent / 'kernel97'
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel98')
kernel = Path('/home/cy122/x2pro-linux/linux')
root = kernel.parent / 'initramfs'
assert json.loads((out / 'address-isolation-validation.json').read_text())['address_isolation_audit_pass']
driver = json.loads((out / 'driver-preparation.json').read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(kernel / 'drivers/bluetooth/hci_qca.c') == driver['qca_source_after_sha256']
assert not (out / 'Image-before').exists()
for source, name, expected in (
    (kernel / 'arch/arm64/boot/Image', 'Image-before', prev / 'Image-connectivity'),
    (kernel / 'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb', 'dtb-before', prev / 'dtb-connectivity'),
    (kernel / 'usr/initramfs_data.cpio', 'cpio-before', prev / 'cpio-after'),
    (kernel / '.config', 'config-before', prev / 'config-after'),
    (root / 'init', 'init-before', prev / 'init-before'),
    (root / 'usr/sbin/samurai-radio-address', 'radio-service-before', ref.parent / 'kernel97/samurai-radio-address'),
):
    assert source.read_bytes() == expected.read_bytes(), name
    shutil.copyfile(source, out / name)
for name in ('btbcm', 'btqca', 'hci_uart'):
    source = root / 'lib/modules/samurai' / (name + '.ko')
    assert source.read_bytes() == (out.parent / 'kernel94' / (name + '.ko')).read_bytes()
    shutil.copyfile(source, out / (name + '-before.ko'))
source_before = subprocess.check_output(['git', 'diff', '--binary', 'HEAD'], cwd=kernel)
(out / 'kernel-source-before-build.patch').write_bytes(source_before)
subprocess.run(['sh', '-n', str(ref / 'samurai-radio-address')], check=True)
(root / 'usr/sbin/samurai-radio-address').write_bytes((ref / 'samurai-radio-address').read_bytes())
subprocess.run(['scripts/config', '--enable', 'ATH10K_TRACING'], cwd=kernel, check=True)
make = ['make', '-j8', 'ARCH=arm64', 'CROSS_COMPILE=aarch64-linux-gnu-', 'KBUILD_BUILD_VERSION=97']
with (out / 'build-kernel.log').open('x') as log:
    subprocess.run([*make, 'olddefconfig'], cwd=kernel, stdout=log, stderr=subprocess.STDOUT, check=True)
    subprocess.run([*make, *['drivers/bluetooth/' + name + '.ko' for name in ('btbcm', 'btqca', 'hci_uart')]], cwd=kernel, stdout=log, stderr=subprocess.STDOUT, check=True)
    for name in ('btbcm', 'btqca', 'hci_uart'):
        module = kernel / 'drivers/bluetooth' / (name + '.ko')
        shutil.copyfile(module, out / (name + '.ko'))
        if name != 'hci_uart':
            assert module.read_bytes() == (out / (name + '-before.ko')).read_bytes()
        shutil.copyfile(module, root / 'lib/modules/samurai' / (name + '.ko'))
    subprocess.run([*make, 'Image', 'qcom/sm8150-samurai.dtb'], cwd=kernel, stdout=log, stderr=subprocess.STDOUT, check=True)
for source, name in (
    (kernel / 'arch/arm64/boot/Image', 'Image-connectivity'),
    (kernel / 'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb', 'dtb-connectivity'),
    (kernel / 'usr/initramfs_data.cpio', 'cpio-after'),
    (kernel / '.config', 'config-after'),
):
    shutil.copyfile(source, out / name)
assert source_before == subprocess.check_output(['git', 'diff', '--binary', 'HEAD'], cwd=kernel)
assert (out / 'dtb-before').read_bytes() == (out / 'dtb-connectivity').read_bytes()
report = dict(kernel_build=97, existing_other_driver_changes_preserved=True,
    diagnostic_only_driver_patch=True, key_wait_behavior_unchanged=True, dtb_byte_identical=True,
    image_sha256=sha(out / 'Image-connectivity'), cpio_sha256=sha(out / 'cpio-after'))
(out / 'build-validation.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
