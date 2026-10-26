from pathlib import Path
import runpy
import re

r=Path('/mnt/e/RealmeX2Pro edk2')
out=Path('/mnt/e/edk2-samurai-out/kernel136')
for path in [out/'oem-adreno_a6xx.c',out/'decoded-legacy-core-private.txt']:
    lines=path.read_text().splitlines()
    for i,line in enumerate(lines):
        if 'RB_CCU_DBG_ECO_CNTL' in line:
            print(path.name,i+1,'\n'.join(lines[max(0,i-3):i+5]))
runpy.run_path(str(r/'reference/kernel118/ensure-build-volume.py'))
base=Path('/home/cy122/pmos-samurai-kernel118/mesa-offline/mesa-26.2.4')
for name in ['src/freedreno/common/freedreno_devices.py', 'src/gallium/drivers/freedreno/a6xx/fd6_emit.cc']:
    path=base/name
    lines=path.read_text().splitlines()
    for i,line in enumerate(lines):
        if 'RB_CCU_DBG_ECO_CNTL' in line or (name.endswith('.py') and ('A640' in line or 'GPUId(640)' in line)):
            print(name,i+1,'\n'.join(lines[max(0,i-4):i+10]))
