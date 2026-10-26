from pathlib import Path
import runpy
import re

ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel146')
runpy.run_path(str(ref.parent / 'kernel118/ensure-build-volume.py'))
mesa=Path('/home/cy122/pmos-samurai-kernel118/mesa-offline/mesa-26.2.4')
text=Path('/mnt/e/edk2-samurai-out/kernel146/baseline145-decoded-private/devcd1-private.data.txt').read_text()
for line in text.splitlines():
    if re.search(r'RB_(?:MRT\[0\].(?:BASE|BUF_INFO)|DEPTH_BUFFER_BASE|DEPTH_BUFFER_INFO|RESOLVE_SYSTEM_BUFFER_BASE|RESOLVE_SYSTEM_BUFFER_INFO|RESOLVE_CNTL|A2D_DEST_BUFFER_BASE|C[CU]|DEPTH_FLAG|MRT_FLAG)',line):
        print(line)
lines=text.splitlines()
for i,line in enumerate(lines):
    if 'ESTIMATED CRASH LOCATION' in line:
        print('\n'.join(lines[max(0,i-45):i+15]))
for name in ['src/gallium/drivers/freedreno/a6xx/fd6_gmem.cc','src/gallium/drivers/freedreno/a6xx/fd6_blitter.cc','src/freedreno/common/fd6_gmem_cache.h']:
    p=mesa / name
    if not p.exists(): continue
    lines=p.read_text().splitlines()
    for i,line in enumerate(lines):
        if 'fd6_emit_gmem2mem' in line or 'RESOLVE_SYSTEM_BUFFER_BASE' in line or 'RB_CCU_CNTL' in line:
            print(name,i+1,'\n'.join(lines[max(0,i-4):i+20]))
