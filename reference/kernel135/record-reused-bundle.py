from pathlib import Path
import json
import hashlib
import runpy
import os
import stat
r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel135'
out = Path('/mnt/e/edk2-samurai-out/kernel135')
oldref = r / 'reference/kernel134'
prior = json.loads((oldref / 'complete-bundle-validation.json').read_text())
boot = json.loads((ref / 'boot-package-validation.json').read_text())
runtime = json.loads((ref / 'failed-runtime-validation.json').read_text())
assert runtime['new_boot_verified'] and runtime['candidate_rejected']
assert prior['matching_boot_logdump_rootfs_modules_complete']
assert prior['decoded_encoded_image_actual_unprivileged_create_read_write_unlink_pass']
runpy.run_path(str(r / 'reference/kernel129/ensure-rootfs-volume.py'))
root = Path('/home/cy122/pmos-samurai-rootfs129/image-export134-fixed')
source = Path('/home/cy122/pmos-samurai-rootfs129/rootfs134')
assert (root.stat().st_uid, root.stat().st_gid, stat.S_IMODE(root.stat().st_mode)) == (0, 0, 0o755)
assert sorted(p.name for p in (root / 'usr/lib/modules').iterdir()) == [boot['release']]
# DT and Linux Image are loaded from the separate logdump partition; no rootfs copy is stale.
for base in [root, source]:
    assert not list((base / 'boot').rglob('*.dtb'))
    assert not list((base / 'boot').rglob('Image*'))
    assert sum(l.startswith('P:') for l in (base / 'lib/apk/db/installed').read_text().splitlines()) == 936
    assert (base / 'etc/init.d/bluetooth').read_bytes() == (r / 'reference/kernel130/bluetooth').read_bytes()
    assert b'AutoEnable=false\n' in (base / 'etc/bluetooth/main.conf').read_bytes()
    assert (base / 'etc/NetworkManager/system-connections/samurai-wifi.nmconnection').read_bytes() == (out.parent / 'kernel128/wifi-dual-band-candidate-private.nmconnection').read_bytes()
    assert (base / 'home/cy122').stat().st_uid == 10000
pid = os.fork()
if pid == 0:
    try:
        os.chroot(root)
        os.chdir('/')
        os.setgroups([])
        os.setgid(10000)
        os.setuid(10000)
        path = '/home/cy122/.local/.samurai-variant135-permission-probe'
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        os.write(fd, b'VARIANT135_HOME_WRITE')
        os.lseek(fd, 0, 0)
        assert os.read(fd, 64) == b'VARIANT135_HOME_WRITE'
        os.close(fd)
        os.unlink(path)
        os._exit(0)
    except BaseException:
        os._exit(1)
assert os.waitpid(pid, 0)[1] == 0
items = []
for role, name in [('boot', 'boot-partition-k135-mdss-reset.img'), ('logdump', 'logdump-k135-mdss-reset.img')]:
    items.append(dict(role=role, name=name, bytes=boot[role + '_bytes'], sha256=boot[role + '_sha256'], artifact_path='E:/edk2-samurai-out/kernel135/' + name))
items += [dict(a) for a in prior['artifacts'] if a['role'] in ['modules', 'rootfs']]
for a in items:
    p = Path('/mnt/e') / a['artifact_path'].removeprefix('E:/')
    assert p.stat().st_size == a['bytes']
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(8 * 1024**2), b''):
            h.update(chunk)
    assert h.hexdigest() == a['sha256']
report = dict(dt_variant=135, software_generation=134, candidate_kernel=134,
    release=boot['release'], rootfs_generation=134, matching_boot_logdump_rootfs_modules_complete=True,
    artifacts=items, software_packages=936, kernel_modules=770,
    encoded_image_entries_verified=21137, rootfs_contains_no_separate_kernel_or_dtb=True,
    encoded_rootfs_reused_byte_exact_from134=True, reused_modules_verified_on_actual_new_boot=True,
    decoded_encoded_image_actual_unprivileged_create_read_write_unlink_pass=True,
    rootfs_bulk_image_not_deployed=True, userdata_erased=False,
    first_automatic_desktop_startup_this_boot_pass=False, candidate_rejected=True,
    candidate_boot_must_not_be_used_as_stable_baseline=True, permanent_display_fix=False,
    gpu_overall_acceptance=False, charging_control_accepted=False, physical_camera_accepted=False,
    hardware_complete=False, goal_complete=False)
for folder in [ref, out]:
    (folder / 'complete-bundle-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('K135_VARIANT_MATCHING_FOUR_ARTIFACTS_WITH_BYTE_EXACT134_ROOTFS_AND_MODULES_PASS', flush=True)
