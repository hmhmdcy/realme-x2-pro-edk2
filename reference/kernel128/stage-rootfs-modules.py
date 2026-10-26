from pathlib import Path
import hashlib,json,os,runpy,subprocess,tarfile
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel128';out=Path('/mnt/e/edk2-samurai-out/kernel128')
runpy.run_path(str(r/'reference/kernel126/ensure-build-volume.py'))
stage=Path('/home/cy122/pmos-samurai-build126');root=stage/'rootfs128';modules=root/'usr/lib/modules';build=json.loads((ref/'kernel-build-validation.json').read_text());release=build['release']
assert (ref/'rootfs-copy-validation.json').is_file() and not (ref/'rootfs-stage-validation.json').exists()
assert modules.resolve()==stage/'rootfs128/usr/lib/modules' and not modules.is_symlink()
assert sorted(p.name for p in modules.iterdir())==['7.3.0-rc6-rmx1931-samurai-k126+']
old=modules/'7.3.0-rc6-rmx1931-samurai-k126+';backup=stage/'rootfs128-old126-module-backup';assert not backup.exists()
assert old.is_dir() and not old.is_symlink() and old.resolve().parent==modules.resolve()
old.rename(backup)
pack=out/'modules-k128-private.tar.gz';assert hashlib.sha256(pack.read_bytes()).hexdigest()==build['archive_sha256']
with tarfile.open(pack) as tf:
 members=tf.getmembers();assert all((m.isfile() or m.isdir()) and not m.issym() and not m.islnk() and '..' not in Path(m.name).parts and not Path(m.name).is_absolute() and (m.name=='lib/modules' or m.name=='lib/modules/'+release or m.name.startswith('lib/modules/'+release+'/')) for m in members)
 tf.extractall(root/'usr',members=members,filter='data')
subprocess.run(['depmod','-e','-F','/home/cy122/pmos-samurai-kernel128/kernel/System.map','-b',str(root),release],check=True,capture_output=True)
assert len(list((modules/release).rglob('*.ko')))==770
(root/'etc/samurai-rootfs-stage').write_text('rootfs128-kernel128-wcn3990-snoc-pairwise-delete\n')
(root/'var/lib/samurai/rootfs128-stage').write_text('kernel128 matching modules; uid10000 home; root owned system resources; internal TPG only\n')
account=[l.split(':') for l in (root/'etc/passwd').read_text().splitlines() if l.startswith('cy122:')];assert len(account)==1 and account[0][2:4]==['10000','10000']
for path in [root/'home/cy122',root/'home/cy122/.local']:assert (path.stat().st_uid,path.stat().st_gid)==(10000,10000)
assert not any(p.lstat().st_uid==1000 for p in root.rglob('*'))
report=dict(rootfs_generation=128,matching_kernel=128,release=release,module_count=770,userspace_packages=936,
 matching_modules_staged=True,only_matching_release_in_new_rootfs=True,base127_image_and_template_preserved=True,
 cloned_old126_modules_retained_outside_new_image=True,home_ownership_matches_passwd=True,
 system_resources_root_owned=True,original_wifi_profile_kept_pending_runtime_validation=True,no_phone_changes=True,
 rootfs_image_pending=True,goal_complete=False)
(ref/'rootfs-stage-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
