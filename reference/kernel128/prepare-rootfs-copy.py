from pathlib import Path
import hashlib,json,os,runpy,shutil,subprocess
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel128'
runpy.run_path(str(r/'reference/kernel126/ensure-build-volume.py'))
stage=Path('/home/cy122/pmos-samurai-build126');base=stage/'rootfs127';root=stage/'rootfs128'
assert not root.exists() and shutil.disk_usage(stage).free>8*1024**3
assert json.loads((r/'reference/kernel127/complete-bundle-validation.json').read_text())['rootfs_home_ownership_matches_passwd']
subprocess.run(['cp','-a','-T',str(base),str(root)],check=True,timeout=300)
count=0
for source in [base,*base.rglob('*')]:
 target=root/source.relative_to(base);a=source.lstat();b=target.lstat()
 assert (a.st_mode,a.st_uid,a.st_gid)==(b.st_mode,b.st_uid,b.st_gid)
 assert os.listxattr(source,follow_symlinks=False)==os.listxattr(target,follow_symlinks=False)
 for name in os.listxattr(source,follow_symlinks=False):assert os.getxattr(source,name,follow_symlinks=False)==os.getxattr(target,name,follow_symlinks=False)
 if source.is_symlink():assert os.readlink(source)==os.readlink(target)
 elif source.is_file():assert hashlib.sha256(source.read_bytes()).digest()==hashlib.sha256(target.read_bytes()).digest()
 else:assert a.st_rdev==b.st_rdev
 count+=1
report=dict(rootfs_generation=128,base127_preserved=True,copy_entries=count,
 copied_all_content_types_owners_modes_links_xattrs_and_devices_verified=True,
 original_passwd_matching_user_permissions_preserved=True,matching128_modules_pending=True,no_phone_changes=True)
(ref/'rootfs-copy-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
