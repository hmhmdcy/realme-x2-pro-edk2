from pathlib import Path
import json,subprocess
root=Path('/home/cy122/x2pro-linux/libcamera214-root');log=root/'work/libcamera/src/libcamera-v0.7.2/output/meson-logs/meson-log.txt';lines=log.read_text(errors='replace').splitlines()
for index,line in enumerate(lines):
    if 'Library yuv' in line or "-lyuv" in line:
        print('\n'.join(lines[max(0,index-12):index+9]))
print(json.dumps([dict(path=str(p.relative_to(root)),symlink=str(p.readlink()) if p.is_symlink() else None) for p in (root/'usr/lib').glob('*yuv*')]))
for args in [['/usr/bin/file','/usr/lib/libyuv.so'],['/usr/bin/scanelf','-n','/usr/lib/libyuv.so']]:
    p=subprocess.run(['chroot',str(root),*args],capture_output=True,text=True,timeout=30);print(json.dumps(dict(args=args,exit=p.returncode,out=p.stdout,err=p.stderr)))
