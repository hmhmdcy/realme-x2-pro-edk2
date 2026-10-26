from pathlib import Path
import hashlib,json,uuid,struct,runpy
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel126/ensure-build-volume.py')
base_ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel128');out=Path('/mnt/e/edk2-samurai-out/kernel128');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel128');stage=Path('/home/cy122/pmos-samurai-build126')
image=out/'samurai-rootfs-f2fs-k128-device-fixed.simg';sparse=json.loads((out/'sparse-fixed-validation.json').read_text())
assert sparse['payload_matches_raw_source'] and sparse['skipped_ranges_verified_as_source_holes'] and sparse['expanded_bytes']==119033245696
checks=['Unreachable nat entries','SIT valid block bitmap checking','Hard link checking for regular file','valid_block_count matching with CP','valid_node_count matching with CP (de lookup)','valid_node_count matching with CP (nat lookup)','valid_inode_count matched with CP','free segment_count matched with CP','next block offset is free','other corrupted bugs']
for name in ['fsck-fixed-raw-private.log','fsck-fixed-restored-private.log']:
    text=(out/name).read_text()
    for check in checks:assert any(check in line and '[Ok..]' in line for line in text.splitlines()),(name,check)
    assert 'Done:' in text
# Check actual encoded superblocks against the private existing UUID without
# exposing its value. Formatting/reconstruction cannot silently change root id.
expected_uuid=uuid.UUID(Path('/mnt/e/edk2-samurai-out/kernel109/rootfs-uuid-private.txt').read_text().strip()).bytes
headers=[]
for name in ['samurai-rootfs-f2fs-k128-device-fixed.raw.img','samurai-rootfs-f2fs-k128-device-fixed-restored.raw.img']:
    with (stage/name).open('rb') as f:
        header=f.read(8192)
    for offset in [1024,5120]:
        block=header[offset:offset+3072]
        assert struct.unpack_from('<I',block)[0]==0xf2f52010 and block.count(expected_uuid)==1 and 'pmos_root'.encode('utf-16le') in block
    headers.append(header)
assert headers[0]==headers[1]
h=hashlib.sha256()
with image.open('rb') as f:
    for b in iter(lambda:f.read(4*1024**2),b''):h.update(b)
assert h.hexdigest()==sparse['sha256']
assert json.loads((base_ref/'rootfs-content-validation.json').read_text())['all_770_modules_exactly_match_validated128_archive']
assert json.loads((ref/'image-export-fixed-content-validation.json').read_text())['all_content_and_mode_uid_gid_symlinks_xattrs_match']
export=stage/'image-export128-fixed'
accounts=[l.split(':') for l in (export/'etc/passwd').read_text().splitlines() if l.startswith('cy122:')]
assert len(accounts)==1 and tuple(map(int,accounts[0][2:4]))==(10000,10000)
home=export/accounts[0][5].lstrip('/')
assert (home.stat().st_uid,home.stat().st_gid)==(10000,10000)
assert ((home/'.local').stat().st_uid,(home/'.local').stat().st_gid)==(10000,10000)
assert not any(p.lstat().st_uid==1000 for p in export.rglob('*'))
assert (export/'dev/null').is_char_device()
report=dict(rootfs_stage=128,matching_candidate_kernel=128,full_software_rootfs_created=True,userspace_packages=936,module_count=770,all_module_bytes_match_candidate128=True,userspace_content_and_metadata_base127_verified=True,home_owner_matches_passwd_uid_gid=True,sparse_bytes=image.stat().st_size,expanded_bytes=sparse['expanded_bytes'],sha256=h.hexdigest(),sparse_reconstruction_payload_exact=True,skip_chunks_verified_as_source_holes=True,both_fsck_pass=True,both_superblocks_private_root_uuid_and_label_match=True,encoded_image_full_directory_export_and_content_metadata_check_pass=True,compatible_with_current118_not_claimed=True,image_not_flashed=True,userdata_not_erased=True,hardware_complete=False,goal_complete=False,artifact_path='E:/edk2-samurai-out/kernel128/samurai-rootfs-f2fs-k128-device-fixed.simg')
(out/'rootfs-k128.sha256').write_text(h.hexdigest()+'  samurai-rootfs-f2fs-k128-device-fixed.simg\n')
for folder in [out,ref]:(folder/'rootfs-image-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
