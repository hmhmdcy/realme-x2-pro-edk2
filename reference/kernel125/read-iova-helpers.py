from pathlib import Path
import runpy
r=Path('/mnt/e/RealmeX2Pro edk2');runpy.run_path(str(r/'reference/kernel122/ensure-rootfs-volume.py'));k=Path('/home/cy122/pmos-samurai-rootfs122/camera125/kernel')
t=(k/'drivers/iommu/iova.c').read_text().splitlines();print('IOVA_TOP','\n'.join(t[:170]));print('IOVA_RESERVE_HELPERS','\n'.join(t[410:515]));print('TOOLS_RBTREE_C',(k/'tools/lib/rbtree.c').read_text()[:1200])
p=k/'drivers/of/of_reserved_mem.c';t=p.read_text().splitlines()
for i,l in enumerate(t):
 if any(x in l for x in ['iommu-addresses','of_property_present(node, "reg")','of_property_present(np, "reg")']):print('OF_RESERVED_PURE_IOVA',i+1,'\n'.join(t[max(0,i-7):i+16]))
