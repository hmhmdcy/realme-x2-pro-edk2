from pathlib import Path
import hashlib,json,os,runpy,stat,tarfile
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel129';out=Path('/mnt/e/edk2-samurai-out/kernel129')
runpy.run_path(str(r/'reference/kernel129/ensure-rootfs-volume.py'))
runpy.run_path(str(r/'reference/kernel126/ensure-build-volume.py'))
stage=Path('/home/cy122/pmos-samurai-rootfs129');base=Path('/home/cy122/pmos-samurai-build126/rootfs128');root=stage/'rootfs129';release='7.3.0-rc6-rmx1931-samurai-k129+'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def manifest(folder):
 result={}
 for parent,dirs,files in os.walk(folder,followlinks=False):
  for name in dirs+files:
   p=Path(parent)/name;rel=p.relative_to(folder).as_posix();s=p.lstat()
   if rel.startswith('usr/lib/modules/'):continue
   item=dict(mode=s.st_mode,uid=s.st_uid,gid=s.st_gid,xattrs={n:hashlib.sha256(os.getxattr(p,n,follow_symlinks=False)).hexdigest() for n in os.listxattr(p,follow_symlinks=False)})
   if stat.S_ISREG(s.st_mode):item.update(size=s.st_size,sha256=sha(p))
   elif stat.S_ISLNK(s.st_mode):item['target']=os.readlink(p)
   elif stat.S_ISCHR(s.st_mode) or stat.S_ISBLK(s.st_mode):item['rdev']=s.st_rdev
   result[rel]=item
 return result
before=manifest(base);after=manifest(root);changes=[name for name in sorted(before.keys()|after.keys()) if before.get(name)!=after.get(name)]
expected=['etc/samurai-rootfs-stage','var/lib/samurai/rootfs129-stage']
assert changes==sorted(expected),changes
actual={p.relative_to(root/'usr/lib/modules'/release).as_posix():sha(p) for p in (root/'usr/lib/modules'/release).rglob('*') if p.is_file()}
with tarfile.open(out/'modules-k129-private.tar.gz') as tf:
 modules={m.name.split('/kernel/',1)[1]:hashlib.sha256(tf.extractfile(m).read()).hexdigest() for m in tf if m.isfile() and m.name.endswith('.ko')}
assert len(modules)==770 and all(actual['kernel/'+name]==h for name,h in modules.items())
assert len([l for l in (root/'lib/apk/db/installed').read_text().splitlines() if l.startswith('P:')])==936
report=dict(rootfs_generation=129,matching_kernel=129,userspace_packages=936,module_count=770,
 all_770_modules_exactly_match_validated129_archive=True,base128_content_types_owners_modes_symlinks_xattrs_preserved_except_declared_changes=True,
 declared_non_module_changes=changes,original_credentials_firmware_and_uid10000_home_preserved=True,
 image_ready_for_encoding=True,goal_complete=False)
(ref/'rootfs-content-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
