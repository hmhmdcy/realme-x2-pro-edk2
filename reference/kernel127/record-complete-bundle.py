from pathlib import Path
import json,hashlib,stat,os,runpy
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel127';out=Path('/mnt/e/edk2-samurai-out/kernel127');old=out.parent/'kernel126'
runpy.run_path(str(r/'reference/kernel126/ensure-build-volume.py'))
root=Path('/home/cy122/pmos-samurai-build126/image-export127-fixed');s=root.stat();assert s.st_uid==s.st_gid==0 and stat.S_IMODE(s.st_mode)==0o755
image=json.loads((ref/'rootfs-image-validation.json').read_text());fix=json.loads((ref/'home-owner-fix-validation.json').read_text());live=json.loads((ref/'live-system-owner-validation.json').read_text())
assert image['home_owner_matches_passwd_uid_gid'] and fix['after_actual_unprivileged_read_write_unlink_pass'] and live['metadata_fix_live_deployed']
# Exercise actual permissions in the fully decoded encoded image as uid10000.
pid=os.fork()
if pid==0:
 try:
  os.chroot(root);os.chdir('/');os.setgroups([]);os.setgid(10000);os.setuid(10000)
  assert os.access('/home/cy122',os.W_OK|os.X_OK) and os.access('/home/cy122/.local',os.W_OK|os.X_OK)
  p='/home/cy122/.local/.samurai-encoded-permission-probe';f=os.open(p,os.O_CREAT|os.O_EXCL|os.O_RDWR|os.O_NOFOLLOW,0o600);os.write(f,b'ENCODED_USER_HOME_WRITE');os.lseek(f,0,0);assert os.read(f,64)==b'ENCODED_USER_HOME_WRITE';os.close(f);os.unlink(p);os._exit(0)
 except BaseException:os._exit(1)
assert os.waitpid(pid,0)[1]==0
bundle=json.loads((r/'reference/kernel126/complete-bundle-validation.json').read_text());artifacts=[]
for item in bundle['artifacts']:
 if item['role']=='rootfs':item=dict(role='rootfs',name='samurai-rootfs-f2fs-k127-device-fixed.simg',bytes=image['sparse_bytes'],sha256=image['sha256']);folder=out
 else:folder=old
 path=folder/item['name'];h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
 assert h.hexdigest()==item['sha256'] and path.stat().st_size==item['bytes']
 artifacts.append(dict(item,artifact_path='E:/edk2-samurai-out/'+folder.name+'/'+item['name']))
bundle.update(rootfs_generation=127,artifacts=artifacts,encoded_image_entries_verified=21131,rootfs_home_ownership_matches_passwd=True,rootfs_semantic_owner_fix_required=False,rootfs_bulk_deployable=True,system_resource_owners_root=True,decoded_encoded_image_actual_unprivileged_create_read_write_unlink_pass=True,source60_home_and85_system_resource_owners_fixed=True,metadata_fix_live_deployed=True,rootfs_bulk_image_not_deployed=True,hardware_complete=False,goal_complete=False)
bundle.pop('superseding_rootfs_generation',None)
for folder in [ref,out]:(folder/'complete-bundle-validation.json').write_text(json.dumps(bundle,indent=2)+'\n')
print('K127_MATCHING126_FOUR_ARTIFACTS_AND_ENCODED_USER_HOME_ACTUAL_ACCESS_PASS',flush=True)
