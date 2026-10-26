from pathlib import Path
import ast

r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel134'
prev = r / 'reference/kernel132'
assert not (ref / 'prepare-rootfs.py').exists()
t = (prev / 'prepare-rootfs.py').read_text()
t = t[:t.index("for name in ['pack-rootfs-fixed.sh'")]
t = t.replace("ref = r / 'reference/kernel132'", "ref = r / 'reference/kernel134'")
t = t.replace("out = Path('/mnt/e/edk2-samurai-out/kernel132')", "out = Path('/mnt/e/edk2-samurai-out/kernel134')")
t = t.replace("runpy.run_path(str(r / 'reference/kernel118/ensure-build-volume.py'))", "runpy.run_path(str(ref / 'ensure-build-volume.py'))")
t = t.replace("base = stage / 'rootfs130'", "base = stage / 'rootfs132'")
t = t.replace("root = stage / 'rootfs132'", "root = stage / 'rootfs134'")
# The existing E129 volume already holds the allocation. Only the sparse output
# and small boot packages consume new host space; retain a 4 GiB host reserve.
t = t.replace("shutil.disk_usage('/mnt/e').free > 8 * 1024**3", "shutil.disk_usage('/mnt/e').free > 4 * 1024**3")
t = t.replace("json.loads((prior / 'complete-bundle-validation.json').read_text())", "json.loads((r / 'reference/kernel132/complete-bundle-validation.json').read_text())")
t = t.replace('rootfs_generation=132, matching_kernel=132', 'rootfs_generation=134, matching_kernel=134')
t = t.replace('base130_', 'base132_')
t = t.replace("oldrelease = '7.3.0-rc6-rmx1931-samurai-k129+'", "oldrelease = '7.3.0-rc6-rmx1931-samurai-k132+'")
t = t.replace('rootfs132-old129-module-backup', 'rootfs134-old132-module-backup')
t = t.replace('modules-k132-private', 'modules-k134-private')
t = t.replace('/home/cy122/pmos-samurai-kernel118/power132/kernel/System.map', '/home/cy122/pmos-samurai-build134/usb134/kernel/System.map')
t = t.replace('rootfs132-kernel132-persistent-readonly-mp2650', 'rootfs134-kernel134-readonly-usb-input-and-mp2650')
t = t.replace('var/lib/samurai/rootfs132-stage', 'var/lib/samurai/rootfs134-stage')
t = t.replace('kernel132 matching modules; MP2650 persistent observation;', 'kernel134 matching modules; USB input budget and MP2650 readonly observation;')
t = t.replace('all_770_modules_exactly_match_validated132_archive', 'all_770_modules_exactly_match_validated134_archive')
ast.parse(t)
(ref / 'prepare-rootfs.py').write_text(t + "print('K134_FULL936_PACKAGE_ROOTFS_COPY_770_MATCHING_MODULES_AND_METADATA_PRESERVATION_PASS', flush=True)\n")
for name in ['pack-rootfs-fixed.sh', 'verify-sparse-fixed.py', 'export-rootfs-image-fixed.py', 'verify-image-export-fixed.py', 'finalize-rootfs-image.py', 'build-rootfs-image.sh']:
    t = (prev / name).read_text().replace('kernel132', 'kernel134').replace('k132', 'k134').replace('K132', 'K134').replace('rootfs132', 'rootfs134').replace('image-export132', 'image-export134')
    t = t.replace('rootfs_stage=132', 'rootfs_stage=134').replace('matching_candidate_kernel=132', 'matching_candidate_kernel=134')
    t = t.replace('all_module_bytes_match_candidate132', 'all_module_bytes_match_candidate134')
    t = t.replace('all_770_modules_exactly_match_validated132_archive', 'all_770_modules_exactly_match_validated134_archive')
    t = t.replace('userspace_content_and_metadata_base130_verified', 'userspace_content_and_metadata_base132_verified')
    if name.endswith('.py'):
        ast.parse(t)
    (ref / name).write_text(t)
print('K134_ROOTFS_TOOLS_FROM_COMPLETED132_WITH_EXPLICIT_BASE132_AND_BUILD134_READY', flush=True)
