from pathlib import Path
import json
import re
import runpy

out=Path('/mnt/e/edk2-samurai-out/kernel136')
r=Path('/mnt/e/RealmeX2Pro edk2')
p=json.loads((out/'legacy-correlation-private.json').read_text())
maps=[m for m in p['same_vm_ops'] if m['op']=='map']
t=(out/'decoded-legacy-core-private.txt').read_text()
results=[]
for line in t.splitlines():
    m=re.search(r'(RB_(?:MRT\[\d\]\.BASE|[A-Z0-9_]*BASE)):\s*(0x[0-9a-fA-F]{9,})',line)
    if not m:
        continue
    addr=int(m[2],16)
    nearest=min(maps,key=lambda p:abs(p['start']-addr))
    item=dict(register=m[1],nearest_bo_bytes=nearest['size'],offset_from_nearest_bo=addr-nearest['start'],
        within_any_fault_vm_mapped_bo=any(p['start']<=addr<p['start']+p['size'] for p in maps),
        base_mod_64k=addr%65536)
    if item not in results:
        results.append(item)
record=dict(stage=136,register_offsets=results,root_cause_proven=False,goal_complete=False)
(r/'reference/kernel136/resolve-bo-offset-validation.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
runpy.run_path(str(r/'reference/kernel118/ensure-build-volume.py'))
base=Path('/home/cy122/pmos-samurai-kernel118/mesa-offline/mesa-26.2.4')
for path in [base/'src/freedreno/registers/adreno/a6xx.xml',Path('/home/cy122/pmos-samurai-kernel136/kernel/drivers/gpu/drm/msm/msm_gem_vma.c')]:
    lines=path.read_text().splitlines()
    for i,line in enumerate(lines):
        if ('RB_RESOLVE_SYSTEM_FLAG_BUFFER_BASE' in line or 'FLAG_BUFFER_BASE' in line or 'drm_mm_insert' in line or 'drm_gpuvm_bo_obtain' in line):
            print(str(path.name),i+1,'\n'.join(lines[max(0,i-3):i+9]))
