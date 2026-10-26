from pathlib import Path
import json
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel127';base=r/'reference/kernel126'
assert json.loads((ref/'home-owner-fix-validation.json').read_text())['after_actual_unprivileged_read_write_unlink_pass']
for name in ['pack-rootfs-fixed.sh','verify-sparse-fixed.py','export-rootfs-image-fixed.py','verify-image-export-fixed.py','finalize-rootfs-image.py']:
 s=(base/name).read_text().replace('/edk2-samurai-out/kernel126','/edk2-samurai-out/kernel127').replace('/reference/kernel126','/reference/kernel127').replace('k126-device-fixed','k127-device-fixed').replace("stage/'rootfs'","stage/'rootfs127'").replace('root="$stage/rootfs"','root="$stage/rootfs127"').replace("stage/'image-export-fixed'","stage/'image-export127-fixed'").replace('rootfs_stage=126','rootfs_stage=127').replace('rootfs_stage=122','rootfs_stage=127').replace('matching_candidate_kernel=126','matching_candidate_kernel=126').replace("'reference/kernel127/ensure-build-volume.py'","'reference/kernel126/ensure-build-volume.py'").replace('/reference/kernel127/ensure-build-volume.py','/reference/kernel126/ensure-build-volume.py').replace('K122','K127')
 s=s.replace('/reference/kernel127/rootfs-content-validation.json','/reference/kernel127/home-owner-fix-validation.json')
 s=s.replace("assert json.loads((ref/'rootfs-content-validation.json').read_text())['all_770_modules_exactly_match_validated126_archive']","assert json.loads((base_ref/'rootfs-content-validation.json').read_text())['all_770_modules_exactly_match_validated126_archive']")
 if name=='finalize-rootfs-image.py':
  s=s.replace("out=Path('/mnt/e/edk2-samurai-out/kernel127');", "base_ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel126');out=Path('/mnt/e/edk2-samurai-out/kernel127');")
  s=s.replace('all_non_module_userspace_except_verified_bluetooth_release_path_preserved=True','userspace_content_and_modes_preserved_except_new_stage_marker=True,home_owner_matches_passwd_uid_gid=True')
 s=s.replace('rootfs-k126.sha256','rootfs-k127.sha256')
 (ref/name).write_text(s)
print('K127_PRIVATE_F2FS_IMAGE_EXPORT_RECONSTRUCTION_TOOLS_READY')
