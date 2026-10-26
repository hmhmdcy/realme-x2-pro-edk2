from pathlib import Path
import hashlib, json

out=Path('/mnt/e/edk2-samurai-out/kernel114')
image=out/'samurai-rootfs-f2fs.simg'
sparse=json.loads((out/'sparse-validation.json').read_text())
assert sparse['payload_matches_raw_source'] and sparse['skipped_ranges_verified_as_source_holes']
checks=['Unreachable nat entries','SIT valid block bitmap checking','Hard link checking for regular file','valid_block_count matching with CP','valid_node_count matching with CP (de lookup)','valid_node_count matching with CP (nat lookup)','valid_inode_count matched with CP','free segment_count matched with CP','next block offset is free','other corrupted bugs']
for name in ['fsck-raw-private.log','fsck-restored-private.log']:
    text=(out/name).read_text()
    for check in checks:
        assert any(check in line and '[Ok..]' in line for line in text.splitlines()),(name,check)
    assert 'Done:' in text
digest=hashlib.sha256()
with image.open('rb') as f:
    for data in iter(lambda:f.read(4*1024*1024),b''):
        digest.update(data)
assert digest.hexdigest()==sparse['sha256']
(out/'rootfs.sha256').write_text(f'{digest.hexdigest()}  samurai-rootfs-f2fs.simg\n')
report=dict(rootfs_image_created=True,sparse_bytes=image.stat().st_size,expanded_bytes=sparse['expanded_bytes'],
            sha256=digest.hexdigest(),sparse_reconstruction_matches=True,both_fsck_pass=True,package_count=936,
            compatible_running_kernel=113,image_not_flashed=True,userdata_not_erased=True,private_device_specific_image=True,
            hardware_complete=False,goal_complete=False,artifact_path='E:/edk2-samurai-out/kernel114/samurai-rootfs-f2fs.simg',
            final_coreutils_hash_allocation_failure_recovered_with_bounded_python_stream=True)
(out/'rootfs-image-validation.json').write_text(json.dumps(report,indent=2)+'\n')
Path('/mnt/e/RealmeX2Pro edk2/reference/kernel114/rootfs-image-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
