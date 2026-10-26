from pathlib import Path
import runpy,re
r=Path('/mnt/e/RealmeX2Pro edk2');runpy.run_path(str(r/'reference/kernel126/ensure-build-volume.py'));v=Path('/home/cy122/pmos-samurai-build126')
for p in (v/'rootfs/usr/lib/modules/samurai').rglob('*'):
 if p.is_file():
  data=p.read_bytes();print('CUSTOM',p.name,len(data))
  if b'vermagic=' in data:
   a=data.index(b'vermagic=');print(data[a:data.index(0,a)].decode())
for folder in ['etc/init.d','usr/sbin','usr/local/sbin']:
 for p in (v/'rootfs'/folder).glob('*'):
  if p.is_file() and not p.is_symlink() and p.stat().st_size<100000:
   try:t=p.read_text()
   except UnicodeDecodeError:continue
   for line in t.splitlines():
    if 'modules/samurai' in line or 'insmod' in line:print(p.relative_to(v/'rootfs'),line)
for p in (v/'initramfs/usr/sbin').glob('*'):
 if p.is_file():
  try:t=p.read_text()
  except UnicodeDecodeError:continue
  for line in t.splitlines():
   if 'insmod' in line or 'modules' in line:print('INITRAMFS',p.name,line)
