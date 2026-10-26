from pathlib import Path
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel128';old=r/'reference/kernel127'
for name in ['pack-rootfs-fixed.sh','verify-sparse-fixed.py','export-rootfs-image-fixed.py','verify-image-export-fixed.py','finalize-rootfs-image.py']:
 s=(old/name).read_text().replace('kernel127','kernel128').replace('k127','k128').replace('K127','K128').replace('rootfs127','rootfs128').replace('image-export127','image-export128')
 if name=='pack-rootfs-fixed.sh':s=s.replace('home-owner-fix-validation.json','rootfs-stage-validation.json')
 if name=='finalize-rootfs-image.py':
  s=s.replace("base_ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel126')","base_ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel128')")
  s=s.replace("assert json.loads((base_ref/'rootfs-content-validation.json').read_text())['all_770_modules_exactly_match_validated126_archive']","assert json.loads((base_ref/'rootfs-content-validation.json').read_text())['all_770_modules_exactly_match_validated128_archive']")
  s=s.replace('rootfs_stage=127,matching_candidate_kernel=126','rootfs_stage=128,matching_candidate_kernel=128').replace('all_module_bytes_match_candidate126','all_module_bytes_match_candidate128')
  s=s.replace('userspace_content_and_modes_preserved_except_new_stage_marker=True','userspace_content_and_metadata_base127_verified=True')
 (ref/name).write_text(s)
print('K128_MATCHING_KERNEL_COMPLETE_F2FS_SPARSE_AND_REVERSE_EXPORT_TOOLS_READY',flush=True)
