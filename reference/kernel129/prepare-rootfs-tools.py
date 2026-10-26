from pathlib import Path
r=Path('/mnt/e/RealmeX2Pro edk2');old=r/'reference/kernel128';ref=r/'reference/kernel129'
def target(s):return s.replace('kernel128','kernel129').replace('k128','k129').replace('K128','K129').replace('rootfs128','rootfs129').replace('image-export128','image-export129')
def volume(s):return s.replace('reference/kernel126/ensure-build-volume.py','reference/kernel129/ensure-rootfs-volume.py').replace('/home/cy122/pmos-samurai-build126','/home/cy122/pmos-samurai-rootfs129')
s=volume(target((old/'prepare-rootfs-copy.py').read_text()))
s=s.replace("runpy.run_path(str(r/'reference/kernel129/ensure-rootfs-volume.py'))","runpy.run_path(str(r/'reference/kernel129/ensure-rootfs-volume.py'))\nrunpy.run_path(str(r/'reference/kernel126/ensure-build-volume.py'))")
s=s.replace("base=stage/'rootfs127';root=stage/'rootfs129'","base=Path('/home/cy122/pmos-samurai-build126/rootfs128');root=stage/'rootfs129'")
s=s.replace('reference/kernel127/complete-bundle-validation','reference/kernel128/complete-bundle-validation').replace('base127_preserved','base128_preserved')
s=s.replace('rootfs_generation=128','rootfs_generation=129').replace('matching128_modules_pending','matching129_modules_pending')
s=s.replace("count=0","tools=stage/'tools/install-root';assert not tools.exists();tools.parent.mkdir(mode=0o700)\nsubprocess.run(['cp','-a','/home/cy122/pmos-samurai-build126/tools/install-root',str(tools)],check=True,timeout=120)\ncount=0")
(ref/'prepare-rootfs-copy.py').write_text(s)
s=volume(target((old/'stage-rootfs-modules.py').read_text())).replace('samurai-k126+','samurai-k128+').replace('old126-module-backup','old128-module-backup')
s=s.replace('rootfs129-kernel129-wcn3990-snoc-pairwise-delete','rootfs129-kernel129-initial-console-node').replace('kernel129 matching modules; uid10000 home; root owned system resources; internal TPG only','kernel129 matching modules; initramfs console 5:1; uid10000 home; dual-band Wi-Fi; internal TPG only')
s=s.replace('rootfs_generation=128,matching_kernel=128','rootfs_generation=129,matching_kernel=129').replace('base127_image','base128_image').replace('cloned_old126','cloned_old128').replace('original_wifi_profile_kept_pending_runtime_validation','validated128_dual_band_profile_preserved')
(ref/'stage-rootfs-modules.py').write_text(s)
s=volume(target((old/'verify-rootfs-content.py').read_text()))
s=s.replace("stage=Path('/home/cy122/pmos-samurai-rootfs129');base=stage/'rootfs127'", "runpy.run_path(str(r/'reference/kernel126/ensure-build-volume.py'))\nstage=Path('/home/cy122/pmos-samurai-rootfs129');base=Path('/home/cy122/pmos-samurai-build126/rootfs128')")
s=s.replace('rootfs_generation=128,matching_kernel=128','rootfs_generation=129,matching_kernel=129').replace('all_770_modules_exactly_match_validated128','all_770_modules_exactly_match_validated129').replace('base127_content','base128_content')
a=s.index("wifi=ref/");b=s.index('assert changes==',a);s=s[:a]+s[b:]
(ref/'verify-rootfs-content.py').write_text(s)
for name in ['pack-rootfs-fixed.sh','verify-sparse-fixed.py','export-rootfs-image-fixed.py','verify-image-export-fixed.py','finalize-rootfs-image.py']:
 s=volume(target((old/name).read_text()))
 if name=='finalize-rootfs-image.py':
  s=s.replace('rootfs_stage=128,matching_candidate_kernel=128','rootfs_stage=129,matching_candidate_kernel=129').replace('all_module_bytes_match_candidate128','all_module_bytes_match_candidate129').replace('all_770_modules_exactly_match_validated128','all_770_modules_exactly_match_validated129').replace('userspace_content_and_metadata_base127','userspace_content_and_metadata_base128')
 (ref/name).write_text(s)
print('K129_ISOLATED_E_ROOTFS_COPY_MATCHING_MODULES_FULL_ENCODING_AND_REVERSE_TOOLS_PREPARED',flush=True)
