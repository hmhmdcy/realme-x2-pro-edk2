from pathlib import Path
import fcntl
import json
import os
import runpy
import shutil
import subprocess
r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel132'
out = Path('/mnt/e/edk2-samurai-out/kernel132')
assert os.geteuid() == 0
assert json.loads((ref / 'complete-bundle-validation.json').read_text())['decoded_encoded_image_actual_unprivileged_create_read_write_unlink_pass']
assert json.loads((ref / 'redundant-raw-cleanup-validation.json').read_text())['all_targets_fresh_byte_and_hole_reconstruction_proved']
assert not (ref / 'host-volume-validation.json').exists()
runpy.run_path(str(r / 'reference/kernel118/ensure-build-volume.py'))
runpy.run_path(str(r / 'reference/kernel129/ensure-rootfs-volume.py'))
results = []
for name, mount, image, lockname in [
    ('kernel118', Path('/home/cy122/pmos-samurai-kernel118'), Path('/mnt/e/edk2-samurai-out/kernel118/build-volume.ext4'), 'samurai-k118-mount.lock'),
    ('rootfs129', Path('/home/cy122/pmos-samurai-rootfs129'), Path('/mnt/e/edk2-samurai-out/kernel129/rootfs-build-volume.ext4'), 'samurai-rfs129-mount.lock')]:
    with (Path('/run/samurai-build-volume-locks') / lockname).open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        sources = subprocess.check_output(['findmnt', '-rn', '-o', 'SOURCE', '--mountpoint', str(mount)], text=True).splitlines()
        assert len(sources) == 1
        assert Path(subprocess.check_output(['losetup', '--noheadings', '--output', 'BACK-FILE', sources[0]], text=True).strip()).resolve() == image.resolve()
        free = shutil.disk_usage(mount).free
        subprocess.run(['sync', '-f', str(mount)], check=True, timeout=30)
        subprocess.run(['umount', str(mount)], check=True, timeout=30)
        assert not mount.is_mount() and not subprocess.check_output(['losetup', '-j', str(image)], text=True).strip()
        with (out / (name + '-volume-offline-readonly-fsck-private.txt')).open('w') as log:
            p = subprocess.run(['e2fsck', '-fn', str(image)], stdout=log, stderr=subprocess.STDOUT, timeout=90)
        assert p.returncode == 0
        results.append(dict(volume=name, unmounted=True, inner_volume_free_bytes=free, offline_readonly_fsck_exit=0))
        print('K132_PRIVATE_VOLUME_UNMOUNT_AND_READONLY_FSCK_PASS', name, flush=True)
for stage, filename, mount in [(122, 'rootfs-build-volume.ext4', 'pmos-samurai-rootfs122'), (126, 'build-volume.ext4', 'pmos-samurai-build126')]:
    target = Path('/mnt/e/edk2-samurai-out') / ('kernel' + str(stage)) / filename
    assert target.is_file() and not Path('/home/cy122', mount).is_mount()
    assert not subprocess.check_output(['losetup', '-j', str(target)], text=True).strip()
report = dict(volumes=results, both_current_private_volumes_unmounted_and_offline_readonly_fsck_zero=True,
              stable122_126_private_volumes_still_unmounted=True,
              host_c_free_bytes=shutil.disk_usage('/mnt/c').free, host_e_free_bytes=shutil.disk_usage('/mnt/e').free,
              original_wsl_vhd_not_fscked_resized_or_compacted=True, goal_complete=False)
(ref / 'host-volume-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('K132_PRIVATE_E_VOLUMES_CLOSED', flush=True)
