from pathlib import Path
import runpy,re
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel118/ensure-build-volume.py')
root=Path('/home/cy122/pmos-samurai-kernel118/kernel/drivers/gpu/drm/msm')
for name,patterns in [('msm_gpu.c',['nr_bos','state->bos','snapshot_capture','iommu_fault']),('adreno/adreno_gpu.c',['nr_bos','state->bos ='])]:
    path=root/name;lines=path.read_text().splitlines()
    for i,line in enumerate(lines):
        if any(pattern in line for pattern in patterns):
            print(name,'line',i+1)
            print('\n'.join(lines[max(0,i-6):i+26]))
