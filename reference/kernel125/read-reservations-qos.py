from pathlib import Path
import runpy,re
r=Path('/mnt/e/RealmeX2Pro edk2');runpy.run_path(str(r/'reference/kernel122/ensure-rootfs-volume.py'));k=Path('/home/cy122/pmos-samurai-rootfs122/camera124/kernel')
for n in ['drivers/iommu/of_iommu.c','Documentation/devicetree/bindings/reserved-memory/reserved-memory.yaml','Documentation/devicetree/bindings/reserved-memory/iommu-addresses.yaml']:
 p=k/n
 if p.exists():
  t=p.read_text();print('SOURCE',n,'\n',t[t.index('static enum iommu_resv_type'):t.index('EXPORT_SYMBOL(of_iommu_get_resv_regions)')] if n.endswith('of_iommu.c') else t)
cam=(k/'drivers/media/platform/qcom/camss/camss.c').read_text();lines=cam.splitlines()
for i,l in enumerate(lines):
 if any(s in l for s in ['static int __maybe_unused camss','static int camss_runtime','icc_set_bw','runtime_resume','runtime_suspend']):print('RUNTIME',i+1,'\n'.join(lines[max(0,i-7):i+52]))
base=Path('/mnt/e/edk2-samurai-out/kernel115/camera-reference/aports/device/testing/linux-oneplus-hotdog-mainline616')
for pat in ['0066*','0074*']:
 for p in base.glob(pat):print('REFERENCE',p.name,p.read_text()[:7500])
n=Path('/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source/drivers/media/platform/msm/camera_8150/cam_cpas/cpas_top')
for version in ['100','101','120']:
 p=n/f'cpastop_v175_{version}.h';t=p.read_text();a=t.index('static struct cam_camnoc_specific');b=t.index('static struct',a+20);print('NATIVE_QOS',version,t[a:b])
