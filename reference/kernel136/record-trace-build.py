from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import tarfile

out = Path('/mnt/e/edk2-samurai-out/kernel136')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel136')
stage = Path('/home/cy122/pmos-samurai-kernel136')
k = stage / 'kernel'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
release = (k / 'include/config/kernel.release').read_text().strip()
assert release == '7.3.0-rc6-rmx1931-samurai-k132+'
assert '#136 SMP PREEMPT' in subprocess.check_output(['strings', str(k / 'arch/arm64/boot/Image')], text=True)
assert sha(k / 'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb') == '97501daa5639223c018a19c120bce1dbcf45f60abcd404c406c4ee67821d6aa8'
assert (out / 'trace-depmod-private.log').stat().st_size == 0
logs = '\n'.join((out / name).read_text() for name in ['trace-msm-build-private.log', 'trace-image-build-private.log'])
assert not re.search(r'\b(?:warning|error):', logs)
with tarfile.open(out.parent / 'kernel132/modules-k132-private.tar.gz') as archive:
    expected = {m.name: archive.extractfile(m).read() for m in archive if m.isfile() and m.name.endswith('.ko')}
assert len(expected) == 770
new = {str(p.relative_to(stage / 'modules-root')): p for p in (stage / 'modules-root').rglob('*.ko')}
assert set(expected) == set(new)
different = [name for name in expected if new[name].read_bytes() != expected[name]]
assert not different, different
for name in ['btbcm', 'btqca', 'hci_uart']:
    module = f'lib/modules/{release}/kernel/drivers/bluetooth/{name}.ko'
    assert (stage / 'initramfs/lib/modules/samurai' / (name + '.ko')).read_bytes() == expected[module]
shutil.copy2(k / 'arch/arm64/boot/Image', out / 'Image-k136-vm-trace-private')
baseline = out.parent / 'kernel132/logdump-k132-charger.img'
assert sha(baseline) == 'db6b966975b987cd51e91f9488185b0a5e4a557755cc3b7043f0e6550aa19751'
target = out / 'logdump-k136-vm-trace.img'
assert not target.exists()
shutil.copyfile(baseline, target)
subprocess.run(['mcopy', '-o', '-i', str(target), str(out / 'Image-k136-vm-trace-private'), '::/Image'], check=True)
assert subprocess.check_output(['mcopy', '-i', str(target), '::/Image', '-']) == (out / 'Image-k136-vm-trace-private').read_bytes()
assert subprocess.check_output(['mcopy', '-i', str(target), '::/samurai.dtb', '-']) == (k / 'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb').read_bytes()
assert set(subprocess.check_output(['mdir', '-b', '-s', '-i', str(target), '::'], text=True).splitlines()) == {'::/Image', '::/samurai.dtb'}
check = subprocess.run(['fsck.fat', '-n', str(target)], capture_output=True)
assert check.returncode == 0
(out / 'trace-fat-check-private.txt').write_bytes(check.stdout + check.stderr)
artifacts = [
    ('boot', out.parent / 'kernel132/boot-partition-k132-charger.img'),
    ('logdump', target),
    ('modules', out.parent / 'kernel132/modules-k132-private.tar.gz'),
    ('rootfs', out.parent / 'kernel132/samurai-rootfs-f2fs-k132-device-fixed.simg')]
records = [dict(role=role, bytes=path.stat().st_size, sha256=sha(path), artifact_path=str(path)) for role, path in artifacts]
report = dict(stage=136, kernel_build=136, software_generation=132, release=release,
              instrumentation_only=True, gpu_fix_accepted=False, image_sha256=sha(out / 'Image-k136-vm-trace-private'),
              image_bytes=(out / 'Image-k136-vm-trace-private').stat().st_size,
              new_tracepoints=['msm_gpu_vm_update', 'msm_gpu_vm_switch_enqueue'],
              all_770_modules_byte_identical132=True, initramfs_bt_modules_match=True,
              dtb_byte_identical132=True, boot132_reused=True, complete_rootfs132_reused=True,
              four_artifacts_fresh_hash_verified=True, artifacts=records,
              fat_readback_exact=True, fat_readonly_check_pass=True,
              kernel_build_no_warnings=True, depmod_no_diagnostics=True,
              flash_partitions=['logdump'], deployed=False, goal_complete=False)
for folder in [ref, out]:
    (folder / 'trace-build-package-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({key: value for key, value in report.items() if key != 'artifacts'}, indent=2), flush=True)
