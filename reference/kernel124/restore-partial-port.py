from pathlib import Path
import runpy,shutil
r=Path('/mnt/e/RealmeX2Pro edk2');runpy.run_path(str(r/'reference/kernel122/ensure-rootfs-volume.py'))
v=Path('/home/cy122/pmos-samurai-rootfs122');a=v/'camera123/kernel';b=v/'camera124/kernel'
assert not (r/'reference/kernel124/sm8150-cphy-power-7.3.patch').exists()
for n in ['camss.c','camss.h','camss-csiphy.h','camss-csid.h','camss-csiphy.c']:
 p='drivers/media/platform/qcom/camss/'+n;shutil.copyfile(a/p,b/p)
print('PARTIAL_UNPUBLISHED_PORT_RESTORED_FROM_K123')
