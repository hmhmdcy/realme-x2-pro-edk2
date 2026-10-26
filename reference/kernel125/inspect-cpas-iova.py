from pathlib import Path
import runpy,shutil,re
r=Path('/mnt/e/RealmeX2Pro edk2');runpy.run_path(str(r/'reference/kernel122/ensure-rootfs-volume.py'))
v=Path('/home/cy122/pmos-samurai-rootfs122');k=v/'camera124/kernel';native=Path('/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source/drivers/media/platform/msm/camera_8150')
print('INNER_VOLUME_FREE_BYTES',shutil.disk_usage(v).free)
def section(p,marker,limit=3500):
 t=p.read_text();i=t.index(marker);print('SOURCE',str(p).split('/source/')[-1].split('/camera124/kernel/')[-1],'\n',t[max(0,i-100):i+limit])
for path,marker,size in [('cam_cpas/cpas_top/cam_cpastop_hw.c','cam_cpastop_get_hw_info',6300),('cam_cpas/cpas_top/cam_cpastop_hw.c','static int cam_cpastop_init_hw',3000),('cam_cpas/cpas_top/cam_cpastop_hw.c','cam_cpastop_program_qos',4000)]:
 p=native/path
 if marker in p.read_text():section(p,marker,size)
for name in ['cpastop_v175_100.h','cpastop_v175_101.h','cpastop_v175_120.h']:
 p=native/'cam_cpas/cpas_top'/name;print('TABLE',name,'BYTES',p.stat().st_size);print(p.read_text()[:3100])
for path,marker,size in [('drivers/iommu/dma-iommu.c','iommu_dma_init_domain',4300),('drivers/iommu/dma-iommu.c','iommu_dma_alloc_iova',2500),('drivers/iommu/dma-iommu.c','iommu_dma_get_resv_regions',2500),('drivers/of/device.c','of_dma_configure_id',4300),('drivers/iommu/of_iommu.c','iommu-addresses',2100)]:
 p=k/path
 if p.exists() and marker in p.read_text():section(p,marker,size)
for p in (k/'drivers/media/platform/qcom/camss').glob('*.[ch]'):
 for i,line in enumerate(p.read_text().splitlines()):
  if any(s in line for s in ['runtime_resume','runtime_suspend','icc_set','dma_parms','iommu','resv']):print('CAMSS_CALL',p.name,i+1,line)
