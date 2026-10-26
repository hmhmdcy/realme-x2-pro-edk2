from pathlib import Path
import runpy,shutil,os,stat,json,hashlib,subprocess
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel127';out=Path('/mnt/e/edk2-samurai-out/kernel127');out.mkdir(mode=0o700,exist_ok=True)
runpy.run_path(str(r/'reference/kernel126/ensure-build-volume.py'))
stage=Path('/home/cy122/pmos-samurai-build126');base=stage/'rootfs';root=stage/'rootfs127'
assert not (out/'home-owner-fix-validation.json').exists() and shutil.disk_usage(stage).free>6*1024**3
if root.exists():
 assert (out/'owner-fix-failure-private.json').is_file() and not root.is_symlink()
 assert json.loads((out/'owner-fix-failure-private.json').read_text())['new_home_correct_owner_count']==60
subprocess.run(['cp','-a','-T',str(base),str(root)],check=True,timeout=180)
# Explicitly verify and preserve ownership and special modes. cp -a also keeps
# hard links and device nodes; generic copyfile would convert /dev/null.
for source in [base,*base.rglob('*')]:
 target=root/source.relative_to(base);s=source.lstat();os.chown(target,s.st_uid,s.st_gid,follow_symlinks=False)
 if not source.is_symlink():os.chmod(target,stat.S_IMODE(s.st_mode))
accounts=[l.split(':') for l in (root/'etc/passwd').read_text().splitlines() if l.startswith('cy122:')];assert len(accounts)==1
account=accounts[0];uid=int(account[2]);gid=int(account[3]);assert (uid,gid)==(10000,10000) and account[5]=='/home/cy122'
home=root/account[5].lstrip('/');assert home.is_dir() and not home.is_symlink()
def access_probe():
 pid=os.fork()
 if pid==0:
  try:
   os.chroot(root);os.chdir('/home/cy122/.local');os.setgroups([]);os.setgid(gid);os.setuid(uid)
   name='.samurai-k127-permission-probe'
   fd=os.open(name,os.O_CREAT|os.O_EXCL|os.O_RDWR|os.O_NOFOLLOW,0o600)
   os.write(fd,b'USER_HOME_ACCESS_CHECK');os.lseek(fd,0,0);assert os.read(fd,64)==b'USER_HOME_ACCESS_CHECK';os.close(fd);os.unlink(name);os._exit(0)
  except PermissionError:os._exit(13)
  except BaseException:os._exit(1)
 return os.waitpid(pid,0)[1]>>8
assert access_probe()==13,'Must demonstrate real unprivileged access failure before fix'
changes=[];home_count=0;resource_count=0
for path in root.rglob('*'):
 s=path.lstat()
 if s.st_uid!=1000:continue
 assert s.st_gid==1000
 relative=path.relative_to(root).as_posix()
 is_home=path.is_relative_to(home)
 assert is_home or relative=='etc/samurai-wifi' or relative.startswith('etc/samurai-wifi/') or relative.startswith('usr/lib/firmware/')
 target_uid,target_gid=(uid,gid) if is_home else (0,0)
 home_count+=is_home;resource_count+=not is_home
 assert path.parent.resolve().is_relative_to(root) and not any(p.is_symlink() for p in path.parents if p.is_relative_to(root))
 attributes={n:os.getxattr(path,n,follow_symlinks=False).hex() for n in os.listxattr(path,follow_symlinks=False)}
 content=hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() and not path.is_symlink() else None
 os.chown(path,target_uid,target_gid,follow_symlinks=False)
 if not path.is_symlink():os.chmod(path,stat.S_IMODE(s.st_mode))
 after=path.lstat();assert (after.st_uid,after.st_gid)==(target_uid,target_gid) and after.st_mode==s.st_mode
 assert {n:os.getxattr(path,n,follow_symlinks=False).hex() for n in os.listxattr(path,follow_symlinks=False)}==attributes
 if content:assert hashlib.sha256(path.read_bytes()).hexdigest()==content
 changes.append(path.relative_to(root).as_posix())
assert home_count==60 and resource_count==85 and len(changes)==145 and access_probe()==0
# All root/package/service permissions remain their actual prior ownership.
for source in base.rglob('*'):
 relative=source.relative_to(base);target=root/relative;s=source.lstat();t=target.lstat()
 assert s.st_mode==t.st_mode
 if str(relative) not in changes:assert (s.st_uid,s.st_gid)==(t.st_uid,t.st_gid)
 if source.is_symlink():assert os.readlink(source)==os.readlink(target)
 elif source.is_file():assert hashlib.sha256(source.read_bytes()).digest()==hashlib.sha256(target.read_bytes()).digest()
(root/'var/lib/samurai/rootfs127-stage').write_text('rootfs127 matching kernel126; home ownership matches passwd; internal TPG only\n')
report=dict(rootfs_generation=127,matching_kernel=126,account_uid_gid=[uid,gid],fixed_home_entries=home_count,fixed_system_resource_entries=resource_count,all145_stale_builder_uid_entries_corrected=True,before_actual_unprivileged_create_denied=True,after_actual_unprivileged_read_write_unlink_pass=True,all_existing_content_modes_symlinks_xattrs_preserved=True,all_other_ownership_preserved=True,source126_rootfs_untouched=True,live_phone_home_already_correct=True,no_phone_home_writes=True,new_image_pending=True,goal_complete=False)
(out/'home-owner-fix-validation.json').write_text(json.dumps(report,indent=2)+'\n');(ref/'home-owner-fix-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
