from pathlib import Path
import tarfile,hashlib,json,subprocess,struct,shutil
out=Path('/mnt/e/edk2-samurai-out/kernel126');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel126')
reportpath=out/'obsolete-object-cleanup-validation.json';assert not reportpath.exists()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
stable={}
for number in [109,111,113,115]:
 root=Path(f'/home/cy122/pmos-samurai-kernel{number}/kernel')
 if (root/'arch/arm64/boot/Image').is_file():stable[str(root/'arch/arm64/boot/Image')]=sha(root/'arch/arm64/boot/Image')
assert 115 in [int(Path(p).parents[3].parent.name.removeprefix('pmos-samurai-kernel')) for p in stable]
proofs=[];before_free=shutil.disk_usage('/home/cy122').free
for number,tag in [(110,'rescue'),(112,'startup'),(114,'ipa-disabled-zram')]:
 root=Path(f'/home/cy122/pmos-samurai-kernel{number}/kernel');assert root.is_dir() and not root.is_symlink() and root.resolve()==root
 assert root.parent.parent==Path('/home/cy122') and number not in [109,111,113,115,118,126]
 baseline=out.parent/f'kernel{number}'
 for relative,name in [('arch/arm64/boot/Image','Image-'+tag),('arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','dtb-'+tag),('usr/initramfs_data.cpio','cpio-'+tag)]:assert sha(root/relative)==sha(baseline/name),(number,relative)
 tracked=set(subprocess.check_output(['git','-C',str(root),'ls-files','-z']).decode().split('\0'))
 diff_before=subprocess.check_output(['git','-C',str(root),'diff','--binary'])
 config_before=sha(root/'.config');symvers_before=sha(root/'Module.symvers')
 candidates=[]
 for path in list(root.rglob('*.o'))+[root/'vmlinux']:
  if not path.is_file() or path.is_symlink() or '.git' in path.relative_to(root).parts:continue
  assert path.resolve().is_relative_to(root) and all(not p.is_symlink() for p in path.parents if p.is_relative_to(root))
  relative=path.relative_to(root).as_posix()
  if relative in tracked:continue
  cmd=path.with_name('.'+path.name+'.cmd')
  if not cmd.is_file() or path.name.encode() not in cmd.read_bytes():continue
  header=path.open('rb').read(20)
  if len(header)!=20 or header[:4]!=b'\x7fELF' or header[4:6]!=b'\x02\x01':continue
  typ,machine=struct.unpack_from('<HH',header,16)
  if typ not in [1,2] or machine not in [62,183]:continue
  candidates.append((path,relative,sha(path),path.stat().st_size,path.stat().st_blocks*512))
 assert len(candidates)>3000
 ignored=subprocess.run(['git','-C',str(root),'check-ignore','-z','--stdin'],input='\0'.join(p[1] for p in candidates).encode()+b'\0',capture_output=True,check=True)
 assert set(ignored.stdout.decode().rstrip('\0').split('\0'))==set(p[1] for p in candidates)
 archive=out/f'obsolete-k{number}-objects-recoverable-private.tar.gz';assert not archive.exists()
 with tarfile.open(archive,'w:gz',compresslevel=3) as tf:
  for path,relative,h,size,blocks in candidates:tf.add(path,arcname=relative,recursive=False)
 checked={}
 with tarfile.open(archive) as tf:
  for member in tf:
   assert member.isfile() and not member.issym() and '..' not in Path(member.name).parts and not Path(member.name).is_absolute()
   checked[member.name]=(hashlib.sha256(tf.extractfile(member).read()).hexdigest(),member.size)
 assert checked=={relative:(h,size) for path,relative,h,size,blocks in candidates}
 assert subprocess.check_output(['git','-C',str(root),'diff','--binary'])==diff_before
 for path,relative,h,size,blocks in candidates:
  assert path.resolve().is_relative_to(root) and sha(path)==h
  path.unlink()
 assert sha(root/'.config')==config_before and sha(root/'Module.symvers')==symvers_before
 assert subprocess.check_output(['git','-C',str(root),'diff','--binary'])==diff_before
 assert all((root/name).exists() for name in tracked if name)
 for relative,name in [('arch/arm64/boot/Image','Image-'+tag),('arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','dtb-'+tag),('usr/initramfs_data.cpio','cpio-'+tag)]:assert sha(root/relative)==sha(baseline/name)
 proof=dict(obsolete_stage=number,removed_generated_ignored_elf_files=len(candidates),allocated_bytes=sum(p[4] for p in candidates),archive_bytes=archive.stat().st_size,archive_sha256=sha(archive),archive_all_file_bytes_verified=True,tracked_sources_and_diff_preserved=True,config_symvers_image_dtb_cpio_preserved=True,modules_not_deleted=True)
 proofs.append(proof);(out/f'obsolete-k{number}-cleanup-proof.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof),flush=True)
assert all(sha(Path(p))==h for p,h in stable.items())
report=dict(checks=proofs,generated_object_allocated_bytes_removed=sum(p['allocated_bytes'] for p in proofs),wsl_root_free_before=before_free,wsl_root_free_after=shutil.disk_usage('/home/cy122').free,stable109_111_113_115_images_unchanged=True,stable118_e_volume_and_rollback_not_deleted=True,recoverable_private_archives_verified=True,no_wsl_vhd_resize_or_compaction=True,host_c_free_bytes=shutil.disk_usage('/mnt/c').free,host_e_free_bytes=shutil.disk_usage('/mnt/e').free,goal_complete=False)
for path in [reportpath,ref/reportpath.name]:path.write_text(json.dumps(report,indent=2)+'\n')
print('K126_VERIFIED_OBSOLETE_OBJECT_CLEANUP_COMPLETE_STABLE_BUILDS_PRESERVED',flush=True)
