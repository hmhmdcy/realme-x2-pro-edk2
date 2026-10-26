from pathlib import Path
import runpy,re
r=Path('/mnt/e/RealmeX2Pro edk2');runpy.run_path(str(r/'reference/kernel122/ensure-rootfs-volume.py'));k=Path('/home/cy122/pmos-samurai-rootfs122/camera124/kernel')
def function(p,name):
 t=p.read_text();m=re.search(r'^(?:static )?(?:int|void|bool|dma_addr_t|struct \w+ \*)\s+'+name+r'\(',t,re.M)
 if not m:print('MISSING',name);return
 b=t.index('{',m.end());i=b+1;d=1
 while d:d+=(t[i]=='{')-(t[i]=='}');i+=1
 print('SOURCE',p.name,'FUNCTION',name,'\n',t[m.start():i])
for path,names in [('drivers/iommu/dma-iommu.c',['iommu_dma_init_domain','iommu_dma_alloc_iova']),('drivers/media/platform/qcom/camss/camss.c',['camss_runtime_resume','camss_runtime_suspend']),('drivers/media/platform/qcom/camss/camss-vfe.c',['vfe_get','vfe_put'])]:
 for n in names:function(k/path,n)
for p in [k/'drivers/iommu/of_iommu.c',k/'drivers/iommu/dma-iommu.c']:
 t=p.read_text();lines=t.splitlines()
 for i,l in enumerate(lines):
  if any(x in l for x in ['iommu-addresses','of_iommu_get_resv_regions','of_iommu_alloc_resv','dma_range_map','force_aperture']):print('IOMMU_SNIPPET',p.name,i+1,'\n'.join(lines[max(0,i-8):i+22]))
p=Path('/mnt/e/edk2-samurai-out/kernel115/camera-reference/aports/device/testing/linux-oneplus-hotdog-mainline616/0074-media-qcom-camss-sm8150-add-camnoc-qos-config.patch')
if p.exists():print('REFERENCE_QOS',p.read_text()[-8000:])
else:print('REFERENCE_QOS_NAMES',[p.name for p in p.parent.glob('0074*')])
n=Path('/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source/drivers/media/platform/msm/camera_8150/cam_cpas/cpas_top/cam_cpastop_hw.c')
function(n,'cam_cpastop_poweron')
