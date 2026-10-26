from pathlib import Path
import fcntl
import json
import os
import runpy
import shutil
import subprocess
r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel135'
out = Path('/mnt/e/edk2-samurai-out/kernel135')
assert not (ref / 'host-volume-validation.json').exists()
assert json.loads((ref / 'complete-bundle-validation.json').read_text())['matching_boot_logdump_rootfs_modules_complete']
assert json.loads((ref / 'rollback-runtime-validation.json').read_text())['taint'] == 0
assert json.loads((ref / 'rollback-health-validation.json').read_text())['fault_increments_zero']
assert json.loads((ref / 'stable-rollback-bundle-validation.json').read_text())['matching_stable_four_artifact_hashes_fresh_verified']
names = subprocess.check_output(['ps', '-eo', 'comm='], text=True).splitlines()
assert not any(n.strip() in ['make', 'cc1', 'cc1plus', 'clang', 'gcc', 'ld', 'sload.f2fs', 'dump.f2fs', 'fsck.f2fs', 'e2fsck'] for n in names)
specs = [
    (118, 'kernel118', 'pmos-samurai-kernel118', 'build-volume.ext4', 'samurai-k118-mount.lock', 'ensure-build-volume.py'),
    (129, 'rootfs129', 'pmos-samurai-rootfs129', 'rootfs-build-volume.ext4', 'samurai-rfs129-mount.lock', 'ensure-rootfs-volume.py'),
    (122, 'rootfs122', 'pmos-samurai-rootfs122', 'rootfs-build-volume.ext4', 'samurai-rfs122-mount.lock', 'ensure-rootfs-volume.py'),
    (134, 'kernel134', 'pmos-samurai-build134', 'build-volume.ext4', 'samurai-k134-mount.lock', 'ensure-build-volume.py'),
]
results = []
for stage, role, dirname, filename, lockname, helper in specs:
    runpy.run_path(str(r / f'reference/kernel{stage}' / helper))
    mount = Path('/home/cy122') / dirname
    image = out.parent / f'kernel{stage}' / filename
    with (Path('/run/samurai-build-volume-locks') / lockname).open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        sources = subprocess.check_output(['findmnt', '-rn', '-o', 'SOURCE', '--mountpoint', str(mount)], text=True).splitlines()
        assert len(sources) == 1 and sources[0].startswith('/dev/loop')
        assert Path(subprocess.check_output(['losetup', '--noheadings', '--output', 'BACK-FILE', sources[0]], text=True).strip()).resolve() == image.resolve()
        free = shutil.disk_usage(mount).free
        subprocess.run(['sync', '-f', str(mount)], check=True, timeout=60)
        subprocess.run(['umount', str(mount)], check=True, timeout=60)
        assert not mount.is_mount() and not subprocess.check_output(['losetup', '-j', str(image)], text=True).strip()
        with (out / f'{role}-final-offline-readonly-fsck-private.txt').open('w') as log:
            p = subprocess.run(['e2fsck', '-fn', str(image)], stdout=log, stderr=subprocess.STDOUT, timeout=180)
        assert p.returncode == 0
        results.append(dict(volume=role, unmounted=True, inner_volume_free_bytes=free, offline_readonly_fsck_exit=0))
        print('K135_PRIVATE_VOLUME_CLOSED_AND_READONLY_FSCK_PASS', role, flush=True)
image = out.parent / 'kernel126/build-volume.ext4'
assert not Path('/home/cy122/pmos-samurai-build126').is_mount() and not subprocess.check_output(['losetup', '-j', str(image)], text=True).strip()
report = dict(volumes=results, all_four_private_volumes_unmounted_and_offline_readonly_fsck_zero=True,
              stable126_private_volume_still_unmounted=True, host_c_free_bytes=shutil.disk_usage('/mnt/c').free,
              host_e_free_bytes=shutil.disk_usage('/mnt/e').free,
              original_wsl_vhd_not_fscked_resized_or_compacted=True, goal_complete=False)
(ref / 'host-volume-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('K135_PRIVATE_VOLUMES_CLOSED_ORIGINAL_WSL_VHD_PRESERVED', flush=True)
