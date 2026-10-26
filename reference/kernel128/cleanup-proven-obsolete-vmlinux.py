from pathlib import Path
import hashlib,json,subprocess,tarfile,shutil
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel128';out=Path('/mnt/e/edk2-samurai-out/kernel128')
assert json.loads((ref/'redundant-vmlinux-inspection.json').read_text())['all_three_proven']
assert not (out/'obsolete-vmlinux-cleanup-private.json').exists()
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
 return h.hexdigest()
stable={}
for n in [109,111,113,115,128]:
 p=Path(f'/home/cy122/pmos-samurai-kernel{n}/kernel/arch/arm64/boot/Image');assert p.is_file();stable[str(p)]=sha(p)
records=[]
for n,tag in [(110,'rescue'),(112,'startup'),(114,'ipa-disabled-zram')]:
 root=Path(f'/home/cy122/pmos-samurai-kernel{n}/kernel');p=root/'vmlinux'
 assert root.resolve()==root and p.resolve().parent==root and not p.is_symlink() and p.stat().st_nlink==1
 assert 'vmlinux' not in subprocess.check_output(['git','-C',str(root),'ls-files'],text=True).splitlines()
 subprocess.run(['git','-C',str(root),'check-ignore','--quiet','vmlinux'],check=True)
 assert sha(out/f'vmlinux{n}-objcopy-private.Image')==sha(root/'arch/arm64/boot/Image')==sha(out.parent/f'kernel{n}'/('Image-'+tag))
 preserve=['.config','Module.symvers','arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','usr/initramfs_data.cpio']
 before={name:sha(root/name) for name in preserve};diff=subprocess.check_output(['git','-C',str(root),'diff','--binary'])
 s=p.stat();digest=sha(p);archive=out/f'obsolete-k{n}-vmlinux-recoverable-private.tar.gz';assert not archive.exists()
 with tarfile.open(archive,'w:gz',compresslevel=3) as tf:tf.add(p,arcname='vmlinux',recursive=False)
 with tarfile.open(archive) as tf:
  members=tf.getmembers();assert len(members)==1 and members[0].name=='vmlinux' and members[0].isfile()
  h=hashlib.sha256()
  f=tf.extractfile(members[0])
  for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
  assert h.hexdigest()==digest and members[0].size==s.st_size
 now=p.stat();assert (now.st_dev,now.st_ino,now.st_mtime_ns,now.st_size)==(s.st_dev,s.st_ino,s.st_mtime_ns,s.st_size) and sha(p)==digest
 assert p.resolve().parent==root and not p.is_symlink() and now.st_nlink==1
 assert subprocess.check_output(['git','-C',str(root),'diff','--binary'])==diff
 p.unlink()
 assert {name:sha(root/name) for name in preserve}==before and subprocess.check_output(['git','-C',str(root),'diff','--binary'])==diff
 records.append(dict(stage=n,allocated_bytes=s.st_blocks*512,archive_bytes=archive.stat().st_size,archive_sha256=sha(archive),archive_member_hash_verified=True,source_diff_and_config_symvers_image_dtb_cpio_preserved=True))
 print('K128_OBSOLETE_VMLINUX_RECOVERABLE_ARCHIVE_VERIFIED_AND_REMOVED',n,flush=True)
assert all(sha(Path(p))==h for p,h in stable.items())
(out/'obsolete-vmlinux-cleanup-private.json').write_text(json.dumps(records,indent=2)+'\n')
report=dict(obsolete_generated_ignored_vmlinux_deleted=3,allocated_bytes_removed=sum(x['allocated_bytes'] for x in records),recoverable_archives_readback_verified=True,canonical_objcopy_image_equivalence_prior_verified=True,stable109_111_113_115_128_images_unchanged=True,stable118_126_e_builds_not_touched=True,remaining_unproven_objects_retained=True,no_recursive_delete=True,wsl_vhd_not_resized_or_compacted=True,host_c_free_bytes=shutil.disk_usage('/mnt/c').free,goal_complete=False)
for folder in [ref,out]:(folder/'obsolete-vmlinux-cleanup-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
