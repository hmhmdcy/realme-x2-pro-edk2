from pathlib import Path
import runpy,json,subprocess,shutil,hashlib,ast,os,struct,errno
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel122/ensure-rootfs-volume.py')
stage=Path('/home/cy122/pmos-samurai-rootfs122');out=Path('/mnt/e/edk2-samurai-out/kernel122');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel122')
assert json.loads((ref/'rootfs-image-validation.json').read_text())['encoded_image_full_directory_export_and_content_metadata_check_pass']
assert json.loads((ref/'image-export-fixed-content-validation.json').read_text())['differing_entries']==0
assert not (ref/'superseded-e-copy-cleanup-validation.json').exists()
code=ast.parse((ref/'cleanup-obsolete-wsl-images.py').read_text());functions=[node for node in code.body if isinstance(node,ast.FunctionDef)]
exec(compile(ast.Module(body=functions,type_ignores=[]),'shared-sparse-reconstruction-proof','exec'),globals())
image=out/'samurai-rootfs-f2fs-k121.simg';assert sha(image)=='27c1c206aedbfac988815bde9e6620234d2ce3e5fe986302e580dc8963ab5772'
files=[stage/'samurai-rootfs-f2fs-k121.raw.img',stage/'samurai-rootfs-f2fs-k121-restored.raw.img']
records=[]
for p in files:
    assert p.resolve().parent==stage and p.is_file() and not p.is_symlink() and not subprocess.check_output(['losetup','-j',str(p)],text=True).strip()
    prove(image,p);s=p.stat();records.append((p,s.st_ino,s.st_mtime_ns,s.st_blocks*512))
export=stage/'image-export-original';assert export.is_dir() and not export.is_symlink() and export.resolve().parent==stage
mounts=subprocess.check_output(['findmnt','-rn','-o','TARGET'],text=True).splitlines();assert not any(p==str(export) or p.startswith(str(export)+'/') for p in mounts)
export_bytes=int(subprocess.check_output(['du','-sx','-B1',str(export)],text=True).split()[0]);before=shutil.disk_usage(stage).free
for p,ino,mtime,allocated in records:
    s=p.stat();assert (s.st_ino,s.st_mtime_ns)==(ino,mtime);p.unlink()
# This is exactly the isolated export from the known failed packaging pass,
# not the source rootfs, corrected export, mounted volume, or rollback archive.
shutil.rmtree(export)
assert all(not p.exists() for p in files) and not export.exists()
assert image.is_file() and (stage/'rootfs').is_dir() and (stage/'image-export-fixed').is_dir()
report=dict(superseded_raw_copies_deleted=2,raw_allocated_bytes_removed=sum(r[3] for r in records),duplicate_failed_export_deleted=True,export_allocated_bytes_removed=export_bytes,first_failed_sparse_image_and_manifests_retained_for_reproduction=True,both_old_raw_copies_freshly_proven_reconstructible=True,corrected_full_rootfs_and_export_preserved=True,private_e_volume_free_before_bytes=before,private_e_volume_free_after_bytes=shutil.disk_usage(stage).free,no_c_or_phone_mutations=True)
(ref/'superseded-e-copy-cleanup-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
