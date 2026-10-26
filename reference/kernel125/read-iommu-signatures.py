from pathlib import Path
import runpy
r=Path('/mnt/e/RealmeX2Pro edk2');runpy.run_path(str(r/'reference/kernel122/ensure-rootfs-volume.py'));k=Path('/home/cy122/pmos-samurai-rootfs122/camera124/kernel')
for name in ['include/linux/iommu.h','drivers/iommu/iommu.c','drivers/media/platform/qcom/camss/Makefile']:
 p=k/name;t=p.read_text().splitlines()
 for i,l in enumerate(t):
  if any(x in l for x in ['iommu_get_resv_regions(','iommu_put_resv_regions(','EXPORT_SYMBOL_GPL(iommu_get_resv_regions)','EXPORT_SYMBOL_GPL(iommu_put_resv_regions)','qcom-camss-objs']):print('SIGNATURE',name,i+1,'\n'.join(t[max(0,i-1):i+8]))
print('CAMSS_MAKEFILE',(k/'drivers/media/platform/qcom/camss/Makefile').read_text())
