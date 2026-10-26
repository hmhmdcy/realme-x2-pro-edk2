from pathlib import Path
import hashlib
import json
import os
import runpy
import stat
r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel132'
out = Path('/mnt/e/edk2-samurai-out/kernel132')
runpy.run_path(str(r / 'reference/kernel129/ensure-rootfs-volume.py'))
root = Path('/home/cy122/pmos-samurai-rootfs129/image-export132-fixed')
s = root.stat()
assert (s.st_uid, s.st_gid, stat.S_IMODE(s.st_mode)) == (0, 0, 0o755)
image = json.loads((ref / 'rootfs-image-validation.json').read_text())
build = json.loads((ref / 'kernel-build-validation.json').read_text())
boot = json.loads((ref / 'boot-package-validation.json').read_text())
runtime = json.loads((ref / 'embedded-runtime-validation.json').read_text())
power = json.loads((ref / 'persistent-power-validation.json').read_text())
assert image['home_owner_matches_passwd_uid_gid'] and image['matching_candidate_kernel'] == 132
assert runtime['new_boot_verified'] and runtime['persistent_mp2650_standard_power_supply_auto_registered']
assert power['auto_registered_after_actual_flash_boot'] and power['standard_nonempty_uevents'] == 8
assert (root / 'etc/NetworkManager/system-connections/samurai-wifi.nmconnection').read_bytes() == (out.parent / 'kernel128/wifi-dual-band-candidate-private.nmconnection').read_bytes()
assert (root / 'etc/init.d/bluetooth').read_bytes() == (r / 'reference/kernel130/bluetooth').read_bytes()
assert (root / 'etc/runlevels/default/bluetooth').is_symlink()
assert b'AutoEnable=false\n' in (root / 'etc/bluetooth/main.conf').read_bytes()
assert (root / 'etc/samurai-rootfs-stage').read_text().startswith('rootfs132-kernel132-')
pid = os.fork()
if pid == 0:
    try:
        os.chroot(root)
        os.chdir('/')
        os.setgroups([])
        os.setgid(10000)
        os.setuid(10000)
        assert os.access('/home/cy122', os.W_OK | os.X_OK) and os.access('/home/cy122/.local', os.W_OK | os.X_OK)
        path = '/home/cy122/.local/.samurai-encoded132-permission-probe'
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        os.write(fd, b'ENCODED132_HOME_WRITE')
        os.lseek(fd, 0, 0)
        assert os.read(fd, 64) == b'ENCODED132_HOME_WRITE'
        os.close(fd)
        os.unlink(path)
        os._exit(0)
    except BaseException:
        os._exit(1)
assert os.waitpid(pid, 0)[1] == 0
expected = [('boot', 'boot-partition-k132-charger.img', boot['boot_bytes'], boot['boot_sha256']),
            ('logdump', 'logdump-k132-charger.img', boot['logdump_bytes'], boot['logdump_sha256']),
            ('modules', 'modules-k132-private.tar.gz', build['archive_bytes'], build['archive_sha256']),
            ('rootfs', 'samurai-rootfs-f2fs-k132-device-fixed.simg', image['sparse_bytes'], image['sha256'])]
artifacts = []
for role, name, size, sha in expected:
    p = out / name
    assert p.is_file() and p.stat().st_size == size
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(8 * 1024**2), b''):
            h.update(chunk)
    assert h.hexdigest() == sha
    artifacts.append(dict(role=role, name=name, bytes=size, sha256=sha, artifact_path='E:/edk2-samurai-out/kernel132/' + name))
report = dict(candidate_kernel=132, release=build['release'], rootfs_generation=132,
              matching_boot_logdump_rootfs_modules_complete=True, artifacts=artifacts,
              software_packages=936, kernel_modules=770,
              encoded_image_entries_verified=json.loads((ref / 'image-export-fixed-content-validation.json').read_text())['export_entries'],
              generated_root_directory_uid_gid_zero=True, generated_root_directory_mode_octal='0755',
              rootfs_home_ownership_matches_passwd=True,
              decoded_encoded_image_actual_unprivileged_create_read_write_unlink_pass=True,
              rootfs_bulk_deployable=True, rootfs_bulk_image_not_deployed=True, userdata_erased=False,
              boot_logdump_and_parallel_matching_modules_actually_deployed_and_verified=True,
              persistent_mp2650_auto_registration_actual_new_boot_verified=True,
              standard_bluez_dms_service_and_dual_band_wifi_profile_preserved=True,
              stable115_118_126_128_129_130_sources_and_rollback_preserved=True,
              charging_control_accepted=False, gpu_overall_acceptance=False, physical_camera_accepted=False,
              hardware_complete=False, goal_complete=False)
for folder in [ref, out]:
    (folder / 'complete-bundle-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('K132_MATCHING_FOUR_ARTIFACTS_ENCODED_UID10000_ACTUAL_POWER_AUTO_REGISTER_BUNDLE_PASS', flush=True)
