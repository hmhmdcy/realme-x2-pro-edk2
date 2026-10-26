from pathlib import Path
import runpy,re
r=Path('/mnt/e/RealmeX2Pro edk2');runpy.run_path(str(r/'reference/kernel122/ensure-rootfs-volume.py'));k=Path('/home/cy122/pmos-samurai-rootfs122/camera124/kernel');b=k/'drivers/media/platform/qcom/camss'
for n,name in [('camss-vfe.c','vfe_set_clock_rates'),('camss.c','vfe_res_8150'),('camss.c','camss_configure_pd')]:
 t=(b/n).read_text();m=re.search(r'^(?:static )?(?:int|const struct camss_subdev_resources) '+name+r'\b',t,re.M);assert m,name;a=m.start();z=t.index('{',a);i=z+1;d=1
 while d:d+=(t[i]=='{')-(t[i]=='}');i+=1
 print('C',name,t[a:i])
print('BUILD_METADATA_PRESENT', (k/'arch/arm64/boot/Image').stat().st_size)
