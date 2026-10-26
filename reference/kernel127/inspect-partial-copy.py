from pathlib import Path
import runpy,os,stat,json,shutil
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel126/ensure-build-volume.py')
stage=Path('/home/cy122/pmos-samurai-build126');root=stage/'rootfs127';out=Path('/mnt/e/edk2-samurai-out/kernel127')
large=[]
if root.exists():
 for p in root.rglob('*'):
  s=p.lstat()
  if stat.S_ISREG(s.st_mode) and s.st_size>100*1024**2:large.append(dict(path=str(p.relative_to(root)),bytes=s.st_size,allocated=s.st_blocks*512))
devices=[]
for p in (stage/'rootfs/dev').rglob('*'):
 s=p.lstat()
 if stat.S_ISCHR(s.st_mode) or stat.S_ISBLK(s.st_mode):devices.append(dict(path=str(p.relative_to(stage/'rootfs')),major=os.major(s.st_rdev),minor=os.minor(s.st_rdev)))
report=dict(partial_rootfs127_exists=root.exists(),large_copied_files=large,original_devices=devices,volume_free_bytes=shutil.disk_usage(stage).free)
(out/'partial-copy-inspection-private.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
