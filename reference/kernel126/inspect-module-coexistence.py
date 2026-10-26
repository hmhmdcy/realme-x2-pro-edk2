from pathlib import Path
import runpy
r=Path('/mnt/e/RealmeX2Pro edk2');runpy.run_path(str(r/'reference/kernel126/ensure-build-volume.py'));v=Path('/home/cy122/pmos-samurai-build126')
print('LOCALVERSION',*[line for line in (v/'kernel/.config').read_text().splitlines() if any(s in line for s in ['CONFIG_LOCALVERSION','CONFIG_INITRAMFS_COMPRESSION','CONFIG_DYNAMIC_DEBUG'])],sep='\n')
print('INIT', (v/'initramfs/init').read_text()[:16000])
runpy.run_path(str(r/'reference/kernel122/ensure-rootfs-volume.py'));root=Path('/home/cy122/pmos-samurai-rootfs122/rootfs')
for folder in ['etc','usr/sbin']:
 for p in (root/folder).rglob('*'):
  if p.is_file() and not p.is_symlink() and p.stat().st_size<100000:
   try:t=p.read_text()
   except UnicodeDecodeError:continue
   if '7.3.0-rc6-rmx1931-samurai' in t:print('HARDCODED_RELEASE',p.relative_to(root),*[line for line in t.splitlines() if '7.3.0-rc6-rmx1931-samurai' in line])
