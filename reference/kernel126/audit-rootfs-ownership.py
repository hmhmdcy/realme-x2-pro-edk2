from pathlib import Path
import runpy,json,collections,os
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel126/ensure-build-volume.py')
root=Path('/home/cy122/pmos-samurai-build126/rootfs');out=Path('/mnt/e/edk2-samurai-out/kernel126')
owners=collections.Counter();privileged=[];selected={}
for path in root.rglob('*'):
 s=path.lstat();owners[(s.st_uid,s.st_gid)]+=1
 if s.st_mode&0o6000:privileged.append(dict(path=path.relative_to(root).as_posix(),uid=s.st_uid,gid=s.st_gid,mode=oct(s.st_mode&0o7777)))
for name in ['etc','usr','etc/passwd','etc/shadow','etc/init.d/sshd','usr/bin/doas','usr/bin/su','usr/bin/busybox']:
 p=root/name
 if p.exists():
  s=p.lstat();selected[name]=dict(uid=s.st_uid,gid=s.st_gid,mode=oct(s.st_mode&0o7777))
report=dict(owner_counts=[dict(uid=u,gid=g,count=n) for (u,g),n in owners.most_common()],privileged=privileged,selected=selected,phone_unchanged=True)
(out/'rootfs-ownership-audit-private.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
