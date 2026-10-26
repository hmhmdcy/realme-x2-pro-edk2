from pathlib import Path
import ast
import hashlib
import json
import os
import runpy
import shutil
import stat
import subprocess
import tarfile
r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel134'
prior = r / 'reference/kernel130'
out = Path('/mnt/e/edk2-samurai-out/kernel134')
runpy.run_path(str(r / 'reference/kernel129/ensure-rootfs-volume.py'))
runpy.run_path(str(ref / 'ensure-build-volume.py'))
stage = Path('/home/cy122/pmos-samurai-rootfs129')
base = stage / 'rootfs132'
root = stage / 'rootfs134'
assert not root.exists() and shutil.disk_usage(stage).free > 8 * 1024**3
assert shutil.disk_usage('/mnt/e').free > 4 * 1024**3
assert json.loads((r / 'reference/kernel132/complete-bundle-validation.json').read_text())['matching_boot_logdump_rootfs_modules_complete']
build = json.loads((ref / 'kernel-build-validation.json').read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
code = (prior / 'prepare-rootfs.py').read_text()
node = next(n for n in ast.parse(code).body if isinstance(n, ast.FunctionDef) and n.name == 'manifest')
scope = {'os': os, 'stat': stat, 'sha': sha}
exec(ast.get_source_segment(code, node), scope)
manifest = scope['manifest']
before = manifest(base)
subprocess.run(['cp', '-a', '-T', str(base), str(root)], check=True, timeout=300)
assert before == manifest(root)
(ref / 'rootfs-copy-validation.json').write_text(json.dumps(dict(rootfs_generation=134, matching_kernel=134,
    base132_preserved=True, copy_entries=len(before), all_content_types_owners_modes_links_xattrs_devices_preserved=True), indent=2) + '\n')
modules = root / 'usr/lib/modules'
oldrelease = '7.3.0-rc6-rmx1931-samurai-k132+'
release = build['release']
assert sorted(p.name for p in modules.iterdir()) == [oldrelease]
old = modules / oldrelease
backup = stage / 'rootfs134-old132-module-backup'
assert not backup.exists() and not old.is_symlink() and old.resolve().parent == modules.resolve()
old.rename(backup)
pack = out / 'modules-k134-private.tar.gz'
assert sha(pack) == build['archive_sha256']
with tarfile.open(pack) as tf:
    members = tf.getmembers()
    assert all((m.isfile() or m.isdir()) and '..' not in Path(m.name).parts and not Path(m.name).is_absolute()
               and (m.name == 'lib/modules' or m.name == 'lib/modules/' + release or m.name.startswith('lib/modules/' + release + '/')) for m in members)
    tf.extractall(root / 'usr', members=members, filter='data')
    expected_modules = {m.name.split('/kernel/', 1)[1]: hashlib.sha256(tf.extractfile(m).read()).hexdigest()
                        for m in members if m.isfile() and m.name.endswith('.ko')}
assert len(expected_modules) == 770
depmod = subprocess.run(['depmod', '-e', '-F', '/home/cy122/pmos-samurai-build134/usb134/kernel/System.map', '-b', str(root), release], capture_output=True, check=True)
assert not depmod.stdout and not depmod.stderr
assert all(sha(modules / release / 'kernel' / name) == h for name, h in expected_modules.items())
(root / 'etc/samurai-rootfs-stage').write_text('rootfs134-kernel134-readonly-usb-input-and-mp2650\n')
(root / 'var/lib/samurai/rootfs134-stage').write_text('kernel134 matching modules; USB input budget and MP2650 readonly observation; standard BlueZ DMS startup; AutoEnable false; uid10000 home; charging control and physical camera pending\n')
after = manifest(root)
changes = [n for n in sorted(before.keys() | after.keys()) if before.get(n) != after.get(n)]
non_modules = [n for n in changes if not n.startswith('usr/lib/modules/' + oldrelease) and not n.startswith('usr/lib/modules/' + release)]
assert non_modules == ['etc/samurai-rootfs-stage', 'var/lib/samurai/rootfs134-stage'], non_modules
assert before == manifest(base)
assert len([l for l in (root / 'lib/apk/db/installed').read_text().splitlines() if l.startswith('P:')]) == 936
assert (root / 'etc/init.d/bluetooth').read_bytes() == (prior / 'bluetooth').read_bytes()
assert (root / 'etc/runlevels/default/bluetooth').is_symlink()
for path in [root / 'home/cy122', root / 'home/cy122/.local']:
    assert (path.stat().st_uid, path.stat().st_gid) == (10000, 10000)
report = dict(rootfs_generation=134, matching_kernel=134, release=release, userspace_packages=936, module_count=770,
              all_770_modules_exactly_match_validated134_archive=True, only_matching_release_in_new_rootfs=True,
              base132_preserved=True, base132_content_types_owners_modes_links_xattrs_devices_preserved_except_declared_changes=True,
              declared_non_module_changes=non_modules, original_credentials_firmware_and_uid10000_home_preserved=True,
              standard_bluez_dms_startup_and_default_service_preserved=True, image_ready_for_encoding=True,
              charging_control_accepted=False, goal_complete=False)
for name in ['rootfs-stage-validation.json', 'rootfs-content-validation.json']:
    (ref / name).write_text(json.dumps(report, indent=2) + '\n')
print('K134_FULL936_PACKAGE_ROOTFS_COPY_770_MATCHING_MODULES_AND_METADATA_PRESERVATION_PASS', flush=True)
