from pathlib import Path
import runpy
root=Path('/mnt/e/RealmeX2Pro edk2');runpy.run_path(str(root/'reference/kernel122/ensure-rootfs-volume.py'))
k=Path('/home/cy122/pmos-samurai-rootfs122/camera124/kernel')
def section(p,a,b):
 t=p.read_text();i=t.index(a);j=t.find(b,i+len(a));print(p.name,t[i:j if j>=0 else i+1800])
base=k/'drivers/media/platform/qcom/camss'
section(base/'camss-csiphy-3ph-1-0.c','static u8 csiphy_get_lane_mask','static void csiphy_hw_version_read')
section(base/'camss-csiphy-3ph-1-0.c','static void csiphy_lanes_enable','static void csiphy_lanes_disable')
for name,start,end in [('camss-csiphy.c',110,169),('camss-csid.c',530,571)]:
 print(name,'\n'.join((base/name).read_text().splitlines()[start:end]))
native=Path('/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source/drivers/media/platform/msm/camera_8150/cam_sensor_module/cam_csiphy/include/cam_csiphy_1_1_hwreg.h')
t=native.read_text();print('NATIVE_TABLE_START_END',t[:2500],t[-3700:])
p=k/'Documentation/devicetree/bindings/media/qcom,sm8150-camss.yaml';print('SCHEMA',p.read_text())
p=Path('/mnt/e/edk2-samurai-out/kernel124/cphy-table-native-private.h');print('GENERATED_TABLE',p.read_text()[:1800])
