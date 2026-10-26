from pathlib import Path
import hashlib
import json
import runpy
import shutil
r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel132'
runpy.run_path(str(r / 'reference/kernel118/ensure-build-volume.py'))
runpy.run_path(str(r / 'reference/kernel129/ensure-rootfs-volume.py'))
records = []
for stage in [128, 129]:
    root = Path('/home/cy122') / ('pmos-samurai-kernel' + str(stage))
    image = root / 'kernel/arch/arm64/boot/Image'
    build = json.loads((r / ('reference/kernel' + str(stage)) / 'kernel-build-validation.json').read_text())
    expected = next(a['sha256'] for a in build['artifacts'] if a['role'] == 'Image')
    assert hashlib.sha256(image.read_bytes()).hexdigest() == expected
    assert (root / 'kernel/.config').is_file() and (root / 'kernel/Makefile').is_file()
    records.append(dict(stage=stage, image_fresh_hash_matches_stable_build=True, source_and_config_present=True))
report = dict(stable_c_builds_fresh_checked=records, c_files_deleted=0,
              unproven_old_c_objects_not_deleted=True, rootfs130_source_export_and_sparse_retained=True,
              verified_redundant130_raw_cleanup_report='redundant-raw-cleanup-validation.json',
              e118_inner_free_bytes=shutil.disk_usage('/home/cy122/pmos-samurai-kernel118').free,
              e129_inner_free_bytes=shutil.disk_usage('/home/cy122/pmos-samurai-rootfs129').free,
              original_wsl_vhd_not_resized_or_compacted=True, goal_complete=False)
(ref / 'host-preservation-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('K132_STABLE_C128_129_IMAGE_HASH_SOURCE_CONFIG_PRESERVATION_PASS', flush=True)
