"""Package the built145 kernel with verified132 system artifacts; no device action."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile

ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel145')
out = Path('/mnt/e/edk2-samurai-out/kernel145')
stage = Path('/home/cy122/pmos-samurai-kernel136')
kernel = stage / 'kernel'
module_root = stage / 'modules-root145'
build = json.loads((ref / 'build-validation.json').read_text())
tests = json.loads((ref / 'actual-function-test-validation.json').read_text())
prior = json.loads(Path('/mnt/e/RealmeX2Pro edk2/reference/kernel144/build-validation.json').read_text())
assert build['image_modules_dtb_build_completed'] and build['three_tracepoints_in_vmlinux']
assert not build['deployed'] and tests['candidate_cases'] == 24
assert tests['baseline_candidate_hardware_effect_signatures_identical']
assert all(row['returncode'] == 0 for row in tests['results'].values())
assert not module_root.exists()
assert not (ref / 'dsi-observation-build-package-validation.json').exists()


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(4 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


image = out / 'Image-k145-dsi-observation-private'
dtb = kernel / 'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'
assert sha(kernel / 'arch/arm64/boot/Image') == sha(image) == build['files'][image.name]['sha256']
assert sha(dtb) == build['files']['sm8150-samurai-k145-private.dtb']['sha256']
assert sha(kernel / 'drivers/gpu/drm/msm/dsi/dsi_host.c') == build['source_sha256']
assert sha(kernel / 'drivers/gpu/drm/msm/msm_dsi_trace.h') == build['trace_header_sha256']
assert sha(kernel / 'drivers/tty/serial/eud.c') == prior['source_sha256']
assert sha(kernel / 'System.map') == build['files']['System-k145-private.map']['sha256']
assert (kernel / '.config').read_bytes() == (out / 'config-before-private').read_bytes()
release = (kernel / 'include/config/kernel.release').read_text().strip()
assert release == '7.3.0-rc6-rmx1931-samurai-k132+'
assert '#145 SMP PREEMPT' in subprocess.check_output(['strings', str(image)], text=True)
assert shutil.disk_usage(stage).free > 256 * 1024**2
for name in ['dsi-object-build-private.log', 'dsi-image-build-private.log']:
    assert not re.search(r'\b(?:warning|error):', (out / name).read_text())

module_root.mkdir(mode=0o700)
env = os.environ.copy()
env['KBUILD_BUILD_VERSION'] = '145'
env['PATH'] = '/home/cy122/.cargo/bin:' + env['PATH']
env['RUSTUP_HOME'] = '/home/cy122/.rustup'
install_log = out / 'dsi-modules-install-private.log'
assert not install_log.exists()
with install_log.open('wb') as stream:
    subprocess.run(['make', 'ARCH=arm64', 'CROSS_COMPILE=aarch64-linux-gnu-',
                    'INSTALL_MOD_PATH=' + str(module_root), 'INSTALL_MOD_STRIP=1',
                    'modules_install'], cwd=kernel, env=env, stdout=stream,
                   stderr=subprocess.STDOUT, check=True)
link = module_root / 'lib/modules' / release / 'build'
assert link.is_symlink() and link.resolve() == kernel.resolve()
link.unlink()
depmod = subprocess.run(['depmod', '-e', '-F', str(kernel / 'System.map'),
                         '-b', str(module_root), release], capture_output=True)
(out / 'dsi-depmod-private.log').write_bytes(depmod.stdout + depmod.stderr)
assert depmod.returncode == 0 and not (depmod.stdout + depmod.stderr)

modules = out.parent / 'kernel132/modules-k132-private.tar.gz'
with tarfile.open(modules) as archive:
    expected = {m.name: archive.extractfile(m).read() for m in archive
                if m.isfile() and m.name.endswith('.ko')}
actual = {str(p.relative_to(module_root)): p for p in module_root.rglob('*.ko')}
assert len(expected) == 770 and actual.keys() == expected.keys()
assert all(actual[name].read_bytes() == content for name, content in expected.items())
for name in ['btbcm', 'btqca', 'hci_uart']:
    assert (stage / 'initramfs/lib/modules/samurai' / (name + '.ko')).read_bytes() == expected[
        f'lib/modules/{release}/kernel/drivers/bluetooth/{name}.ko']
assert (kernel / '.config').read_bytes() == (out / 'config-before-private').read_bytes()
assert sha(kernel / 'arch/arm64/boot/Image') == build['files'][image.name]['sha256']
print('K145_FRESH_MODULE_INSTALL_AND_ALL770_MODULES_IDENTICAL132', flush=True)

baseline = out.parent / 'kernel132/logdump-k132-charger.img'
assert sha(baseline) == 'db6b966975b987cd51e91f9488185b0a5e4a557755cc3b7043f0e6550aa19751'
rollback = out.parent / 'kernel140/logdump-k140-dma-diagnostic.img'
assert sha(rollback) == '0ac9d6678ba4218a049fca47090c4fdd290d03d6a1fd72a6d9f04f046b21d925'
target = out / 'logdump-k145-dsi-observation.img'
assert not target.exists()
shutil.copyfile(baseline, target)
subprocess.run(['mcopy', '-o', '-i', str(target), str(image), '::/Image'], check=True)
assert subprocess.check_output(['mcopy', '-i', str(target), '::/Image', '-']) == image.read_bytes()
assert subprocess.check_output(['mcopy', '-i', str(target), '::/samurai.dtb', '-']) == dtb.read_bytes()
assert set(subprocess.check_output(['mdir', '-b', '-s', '-i', str(target), '::'], text=True).splitlines()) == {'::/Image', '::/samurai.dtb'}
check = subprocess.run(['fsck.fat', '-n', str(target)], capture_output=True)
(out / 'dsi-fat-check-private.txt').write_bytes(check.stdout + check.stderr)
assert check.returncode == 0 and target.stat().st_size == 67108864
artifacts = [
    ('boot', out.parent / 'kernel132/boot-partition-k132-charger.img',
     '501074e6feb3c5e93eff86f40848acbfc102da44e06cf52f95770d80a83d07f6'),
    ('logdump', target, sha(target)),
    ('modules', modules, '92e03906e3f437880590417070640bb0e81fada4638ab2a6dcaf8f57bbae923c'),
    ('rootfs', out.parent / 'kernel132/samurai-rootfs-f2fs-k132-device-fixed.simg',
     '290e7af5fdda219a558032f4f75dfec6979a32e66693f117964361a4fd903ccb'),
]
records = []
for role, path, digest in artifacts:
    assert sha(path) == digest
    records.append(dict(role=role, bytes=path.stat().st_size, sha256=digest, name=path.name))
report = dict(stage=145, kernel_build=145, current_phone_kernel_build_before_deploy=140,
              software_generation=132, release=release,
              dsi_raw_state_trace_only=True, no_new_mmio_or_printk=True,
              eud_handoff144_preserved=True, unsubmitted_unwind139_preserved=True,
              diagnostics140_preserved=True, host_actual_function_cases=24,
              eud_handoff_actual_function_cases=26, image_sha256=sha(image),
              image_bytes=image.stat().st_size, logdump_sha256=sha(target),
              all_770_modules_byte_identical132=True, fresh145_module_install_verified=True,
              initramfs_bt_modules_match=True, dtb_byte_identical132=True,
              boot132_reused=True, complete_rootfs132_reused=True,
              four_artifacts_fresh_hash_verified=True, artifacts=records,
              rollback140_logdump_hash_verified=True, fat_readback_exact=True,
              fat_readonly_check_pass=True, kernel_build_no_warnings=True,
              depmod_no_diagnostics=True, flash_partitions=['logdump'],
              deployed=False, actual_runtime_verified=False, display_accepted=False,
              gpu_accepted=False, charging_accepted=False, goal_complete=False)
for folder in [ref, out]:
    (folder / 'dsi-observation-build-package-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('K145_FOUR_ARTIFACT_PACKAGE_AND_ROLLBACK_VERIFIED_NOT_DEPLOYED', flush=True)
