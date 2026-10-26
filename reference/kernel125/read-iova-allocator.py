from pathlib import Path
import re,runpy
r=Path('/mnt/e/RealmeX2Pro edk2');runpy.run_path(str(r/'reference/kernel122/ensure-rootfs-volume.py'));k=Path('/home/cy122/pmos-samurai-rootfs122/camera125/kernel')
for n in ['drivers/iommu/iova.c','include/linux/iova.h']:
 t=(k/n).read_text()
 if n.endswith('.h'):print('IOVA_HEADER',t[:3800]);continue
 for name in ['__alloc_and_insert_iova_range','reserve_iova','alloc_iova','iova_insert_rbtree','init_iova_domain']:
  m=re.search(r'^.*?\b'+name+r'\(',t,re.M)
  if not m:print('MISSING',name);continue
  start=m.start();b=t.index('{',m.end());i=b+1;d=1
  while d:d+=(t[i]=='{')-(t[i]=='}');i+=1
  print('ALLOCATOR_FUNCTION',name,t[start:i])
print('TOOLS_RBTREE_EXIST',[str(p.relative_to(k)) for p in [k/'tools/lib/rbtree.c',k/'tools/include/linux/rbtree.h',k/'tools/include/linux/rbtree_augmented.h'] if p.exists()])
