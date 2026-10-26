from pathlib import Path
import hashlib,json,os,struct,errno,subprocess,shutil
out=Path('/mnt/e/edk2-samurai-out/kernel122');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel122')
base=Path('/home/cy122/pmos-samurai-rootfs115').resolve();saved=Path('/mnt/e/edk2-samurai-out/kernel115')
assert base==Path('/home/cy122/pmos-samurai-rootfs115') and (base/'rootfs').is_dir()
assert not (out/'obsolete-raw-cleanup-private.json').exists()
pairs=[('samurai-rootfs-f2fs.simg','rootfs-image-validation.json',['samurai-rootfs-f2fs-final.raw.img','samurai-rootfs-f2fs-restored.raw.img']),('samurai-rootfs-f2fs-delay-fixed.simg','rootfs-fixed-image-validation.json',['samurai-rootfs-f2fs-delay-fixed.raw.img','samurai-rootfs-f2fs-delay-fixed-restored.raw.img'])]
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(4*1024**2),b''):h.update(b)
    return h.hexdigest()
def prove(sparse,raw):
    expected=119033245696
    with sparse.open('rb') as f,raw.open('rb') as original:
        magic,major,minor,fh,ch,bs,blocks,chunks,crc=struct.unpack('<I4H4I',f.read(28))
        assert magic==0xed26ff3a and major==1 and bs==4096 and blocks*bs==expected
        f.seek(fh);block_offset=0
        for _ in range(chunks):
            kind,res,n,total=struct.unpack('<2H2I',f.read(12));f.seek(ch-12,1);size=n*bs;offset=block_offset*bs;assert offset+size<=expected;original.seek(offset)
            if kind==0xcac1:
                assert total==ch+size;remaining=size
                while remaining:
                    data=f.read(min(remaining,4*1024**2));assert data and data==original.read(len(data));remaining-=len(data)
            elif kind==0xcac2:
                assert total==ch+4;pattern=f.read(4);remaining=size
                while remaining:
                    step=min(remaining,4*1024**2);assert original.read(step)==pattern*(step//4);remaining-=step
            elif kind==0xcac3:
                assert total==ch
                try:nxt=os.lseek(original.fileno(),offset,os.SEEK_DATA)
                except OSError as e:assert e.errno==errno.ENXIO;nxt=expected
                assert nxt>=offset+size
            elif kind==0xcac4:assert n==0 and total==ch+4;f.read(4)
            else:raise ValueError(kind)
            block_offset+=n
        assert block_offset==blocks and not f.read(1)
records=[];before_c=shutil.disk_usage('/mnt/c').free;before_wsl=shutil.disk_usage('/').free
for image_name,report_name,raw_names in pairs:
    image=saved/image_name;report=json.loads((saved/report_name).read_text())
    assert report['both_fsck_pass'] and report['sparse_reconstruction_matches'] and sha(image)==report['sha256']
    for name in raw_names:
        p=base/name;assert p.resolve().parent==base and p.is_file() and not p.is_symlink()
        assert not subprocess.check_output(['losetup','-j',str(p)],text=True).strip()
        s=p.stat();assert s.st_size==report['expanded_bytes'] and s.st_nlink==1
        prove(image,p)
        records.append(dict(path=str(p),inode=s.st_ino,device=s.st_dev,logical_bytes=s.st_size,allocated_bytes=s.st_blocks*512,mtime_ns=s.st_mtime_ns,retained_image=str(image),retained_image_sha256=report['sha256'],fresh_sparse_payload_and_hole_proof=True))
        print('VERIFIED_OBSOLETE_RAW_COPY',name,flush=True)
(out/'obsolete-raw-cleanup-private.json').write_text(json.dumps(dict(before_c_free_bytes=before_c,before_wsl_free_bytes=before_wsl,records=records),indent=2)+'\n')
# No deletion starts until every target has a fresh reconstruction proof and
# its independently hashed, previously fsck-validated retained sparse image.
for record in records:
    p=Path(record['path']);s=p.stat()
    assert p.resolve().parent==base and (s.st_ino,s.st_dev,s.st_size,s.st_mtime_ns)==(record['inode'],record['device'],record['logical_bytes'],record['mtime_ns'])
    assert not subprocess.check_output(['losetup','-j',str(p)],text=True).strip()
    p.unlink()
with (out/'wsl-root-fstrim-private.txt').open('w') as log:
    trim=subprocess.run(['fstrim','-v','/'],stdout=log,stderr=subprocess.STDOUT,timeout=90)
assert all(not Path(r['path']).exists() for r in records)
assert (base/'rootfs').is_dir() and all((saved/p[0]).is_file() for p in pairs)
report=dict(obsolete_raw_files_deleted=len(records),all_four_freshly_proven_reconstructible_before_delete=True,logical_bytes_removed=sum(r['logical_bytes'] for r in records),allocated_bytes_removed=sum(r['allocated_bytes'] for r in records),retained_sparse_images=2,both_retained_images_hash_and_prior_fsck_verified=True,rootfs115_userspace_stage_preserved=True,current118_and121_sources_and_rollback_images_preserved=True,no_unknown_paths_deleted=True,no_recursive_directory_delete=True,root_fstrim_exit=trim.returncode,c_free_before_bytes=before_c,c_free_after_bytes=shutil.disk_usage('/mnt/c').free,wsl_free_before_bytes=before_wsl,wsl_free_after_bytes=shutil.disk_usage('/').free,original_vhd_not_resized_or_fscked=True,phone_unchanged=True)
(ref/'obsolete-artifact-cleanup-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
