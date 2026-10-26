from pathlib import Path
import urllib.request
import runpy
import hashlib
import json
import re

r=Path('/mnt/e/RealmeX2Pro edk2')
out=Path('/mnt/e/edk2-samurai-out/kernel136')
sources=[]
commit='9668fcdc6ec15be7a10d66f7b93c347829e0fdb6'
for name in ['adreno_a6xx.c','adreno_ringbuffer.c','adreno.c','adreno-gpulist.h']:
    url=f'https://raw.githubusercontent.com/realme-kernel-opensource/realmeX2Pro-kernel-source/{commit}/drivers/gpu/msm/{name}'
    path=out/('oem-'+name)
    if not path.exists():
        with urllib.request.urlopen(url,timeout=30) as response:
            path.write_bytes(response.read())
    sources.append(dict(name=name,url=url,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    lines=path.read_text().splitlines()
    terms=['highest_bank_bit','qcom,highest-bank-bit','KGSL_UBWC_3_0'] if name!='adreno_ringbuffer.c' else ['ccu_invalidate']
    for i,line in enumerate(lines):
        if any(term in line for term in terms):
            print(name,i+1,'\n'.join(lines[max(0,i-4):i+12]))
runpy.run_path(str(r/'reference/kernel118/ensure-build-volume.py'))
base=Path('/home/cy122/pmos-samurai-kernel118/mesa-offline/mesa-26.2.4')
for name in ['src/freedreno/common/freedreno_dev_info.h', 'src/gallium/drivers/freedreno/a6xx/fd6_screen.cc']:
    path=base/name
    if path.exists():
        lines=path.read_text().splitlines()
        for i,line in enumerate(lines):
            if 'ubwc' in line.lower():
                print(name,i+1,'\n'.join(lines[max(0,i-4):i+7]))
t=(out/'decoded-legacy-core-private.txt').read_text()
values=[]
for line in t.splitlines():
    if re.search(r'\b(?:RB|SP|TPL1|UCHE|RBBM)_NC?_?MODE_CNTL',line):
        values.append(re.sub(r'^\s*[0-9a-f]{8}\s+','',line))
print('CORE_UBWC_MODE_REGISTERS',values)
record=dict(stage=136,oem_sources=sources,core_mode_registers=values,
            hbb_debugfs_read_return='EINVAL',ubo_or_ubwc_root_cause_proven=False,
            candidate_packet_reorder_not_applied=True,goal_complete=False)
(r/'reference/kernel136/ubwc-source-contract-validation.json').write_text(json.dumps(record,indent=2)+'\n')
