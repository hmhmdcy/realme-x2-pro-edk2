from pathlib import Path
import hashlib, json, shutil, subprocess

out = Path('/mnt/e/edk2-samurai-out/kernel98')
kernel = Path('/home/cy122/x2pro-linux/linux')
root = kernel.parent / 'initramfs'
assert not (out / 'build-kernel-specific-retry1.log').exists()
assert not (out / 'Image-connectivity').exists()
assert subprocess.check_output(['git', 'diff', '--binary', 'HEAD'], cwd=kernel) == (out / 'kernel-source-before-build.patch').read_bytes()
make = ['make', '-j8', 'ARCH=arm64', 'CROSS_COMPILE=aarch64-linux-gnu-', 'KBUILD_BUILD_VERSION=97']
with (out / 'build-kernel-specific-retry1.log').open('x') as log:
    subprocess.run([*make, *['drivers/bluetooth/' + name + '.ko' for name in ('btbcm', 'btqca', 'hci_uart')]], cwd=kernel, stdout=log, stderr=subprocess.STDOUT, check=True)
    for name in ('btbcm', 'btqca', 'hci_uart'):
        module = kernel / 'drivers/bluetooth' / (name + '.ko')
        shutil.copyfile(module, out / (name + '.ko'))
        if name != 'hci_uart':
            assert module.read_bytes() == (out / (name + '-before.ko')).read_bytes()
        shutil.copyfile(module, root / 'lib/modules/samurai' / (name + '.ko'))
    subprocess.run([*make, 'Image', 'qcom/sm8150-samurai.dtb'], cwd=kernel, stdout=log, stderr=subprocess.STDOUT, check=True)
for source, name in ((kernel/'arch/arm64/boot/Image','Image-connectivity'),
    (kernel/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','dtb-connectivity'),
    (kernel/'usr/initramfs_data.cpio','cpio-after'),(kernel/'.config','config-after')):
    shutil.copyfile(source, out/name)
assert subprocess.check_output(['git', 'diff', '--binary', 'HEAD'], cwd=kernel) == (out / 'kernel-source-before-build.patch').read_bytes()
assert (out/'dtb-before').read_bytes() == (out/'dtb-connectivity').read_bytes()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
report = dict(kernel_build=97, existing_other_driver_changes_preserved=True,
    diagnostic_only_driver_patch=True, key_wait_behavior_unchanged=True, dtb_byte_identical=True,
    initial_overbroad_modules_build_stopped=True, specific_build_retry_pass=True,
    image_sha256=sha(out/'Image-connectivity'),cpio_sha256=sha(out/'cpio-after'))
(out/'build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
