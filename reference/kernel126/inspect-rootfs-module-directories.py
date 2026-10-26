from pathlib import Path
import runpy
r=Path('/mnt/e/RealmeX2Pro edk2');runpy.run_path(str(r/'reference/kernel126/ensure-build-volume.py'))
p=Path('/home/cy122/pmos-samurai-build126/rootfs/usr/lib/modules')
for child in p.iterdir():print(child.name,'symlink',child.is_symlink(),'modules',len(list(child.rglob('*.ko'))))
