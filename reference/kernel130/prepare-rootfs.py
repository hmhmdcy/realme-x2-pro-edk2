from pathlib import Path
import hashlib,json,os,runpy,shutil,stat,subprocess,tarfile
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel130';prev=r/'reference/kernel129';out=Path('/mnt/e/edk2-samurai-out/kernel130')
runpy.run_path(str(prev/'ensure-rootfs-volume.py'))
stage=Path('/home/cy122/pmos-samurai-rootfs129');base=stage/'rootfs129';root=stage/'rootfs130'
assert not root.exists() and shutil.disk_usage(stage).free>8*1024**3
assert json.loads((prev/'complete-bundle-validation.json').read_text())['matching_boot_logdump_rootfs_modules_complete']
subprocess.run(['cp','-a','-T',str(base),str(root)],check=True,timeout=300)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def manifest(folder):
 result={}
 for p in [folder,*folder.rglob('*')]:
  s=p.lstat();item=dict(mode=s.st_mode,uid=s.st_uid,gid=s.st_gid,xattrs={n:hashlib.sha256(os.getxattr(p,n,follow_symlinks=False)).hexdigest() for n in os.listxattr(p,follow_symlinks=False)})
  if stat.S_ISREG(s.st_mode):item.update(size=s.st_size,sha256=sha(p))
  elif stat.S_ISLNK(s.st_mode):item['target']=os.readlink(p)
  elif stat.S_ISCHR(s.st_mode) or stat.S_ISBLK(s.st_mode):item['rdev']=s.st_rdev
  result[p.relative_to(folder).as_posix()]=item
 return result
before=manifest(base);assert before==manifest(root)
(ref/'rootfs-copy-validation.json').write_text(json.dumps(dict(rootfs_generation=130,matching_kernel=129,base129_preserved=True,copy_entries=len(before),all_content_types_owners_modes_links_xattrs_devices_preserved=True),indent=2)+'\n')
p=root/'etc/init.d/bluetooth';assert 'need dbus localmount hostname' in p.read_text() and 'start_pre' not in p.read_text();p.write_bytes((ref/'bluetooth').read_bytes());os.chown(p,0,0);os.chmod(p,0o755)
p=root/'etc/bluetooth/main.conf';data=p.read_bytes();assert data.count(b'#AutoEnable=true\n')==1;p.write_bytes(data.replace(b'#AutoEnable=true\n',b'AutoEnable=false\n'));os.chown(p,0,0);os.chmod(p,0o644)
p=root/'etc/runlevels/default/bluetooth';assert not p.exists() and not p.is_symlink();p.symlink_to('/etc/init.d/bluetooth');os.lchown(p,0,0)
(root/'etc/samurai-rootfs-stage').write_text('rootfs130-kernel129-standard-bluez-dms-startup\n')
(root/'var/lib/samurai/rootfs130-stage').write_text('kernel129 matching modules; initramfs console 5:1; verified DMS identity before BlueZ; standard OpenRC service enabled; AutoEnable false; uid10000 home; dual-band Wi-Fi; physical camera pending\n')
after=manifest(root);changes=[n for n in sorted(before.keys()|after.keys()) if before.get(n)!=after.get(n)]
expected=['etc/init.d/bluetooth','etc/bluetooth/main.conf','etc/runlevels/default/bluetooth','etc/samurai-rootfs-stage','var/lib/samurai/rootfs130-stage'];assert changes==sorted(expected),changes
release='7.3.0-rc6-rmx1931-samurai-k129+'
with tarfile.open(out.parent/'kernel129/modules-k129-private.tar.gz') as tf:
 modules={m.name.split('/kernel/',1)[1]:hashlib.sha256(tf.extractfile(m).read()).hexdigest() for m in tf if m.isfile() and m.name.endswith('.ko')}
assert len(modules)==770 and all(sha(root/'usr/lib/modules'/release/'kernel'/n)==h for n,h in modules.items())
assert len([l for l in (root/'lib/apk/db/installed').read_text().splitlines() if l.startswith('P:')])==936
report=dict(rootfs_generation=130,matching_kernel=129,userspace_packages=936,module_count=770,all_770_modules_exactly_match_validated129_archive=True,
 base129_content_types_owners_modes_symlinks_xattrs_preserved_except_declared_changes=True,declared_non_module_changes=changes,
 original_credentials_firmware_and_uid10000_home_preserved=True,standard_bluez_dms_address_startup_and_default_service_enabled=True,controller_not_auto_powered=True,
 image_ready_for_encoding=True,goal_complete=False)
(ref/'rootfs-stage-validation.json').write_text(json.dumps(report,indent=2)+'\n');(ref/'rootfs-content-validation.json').write_text(json.dumps(report,indent=2)+'\n')
for name in ['pack-rootfs-fixed.sh','verify-sparse-fixed.py','export-rootfs-image-fixed.py','verify-image-export-fixed.py','finalize-rootfs-image.py']:
 s=(prev/name).read_text().replace('kernel129','kernel130').replace('k129','k130').replace('K129','K130').replace('rootfs129','rootfs130').replace('image-export129','image-export130')
 s=s.replace('reference/kernel130/ensure-rootfs-volume.py','reference/kernel129/ensure-rootfs-volume.py').replace('/home/cy122/pmos-samurai-rootfs130','/home/cy122/pmos-samurai-rootfs129')
 s=s.replace('all_770_modules_exactly_match_validated129_archive','all_770_modules_exactly_match_validated129_archive')
 if name=='finalize-rootfs-image.py':
  s=s.replace('rootfs_stage=129,matching_candidate_kernel=129','rootfs_stage=130,matching_candidate_kernel=129').replace('userspace_content_and_metadata_base128_verified','userspace_content_and_metadata_base129_verified')
 if name=='pack-rootfs-fixed.sh': s=s.replace('stage=/home/cy122/pmos-samurai-rootfs129','stage=/home/cy122/pmos-samurai-rootfs129')
 (ref/name).write_text(s)
print(json.dumps(report),flush=True)
