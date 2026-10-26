from pathlib import Path
import runpy,re
r=Path('/mnt/e/RealmeX2Pro edk2');runpy.run_path(str(r/'reference/kernel122/ensure-rootfs-volume.py'));k=Path('/home/cy122/pmos-samurai-rootfs122/camera125/kernel');d=k/'drivers/media/platform/qcom/camss'
for filename,names in [('camss-video.c',['video_buf_init','video_prepare_streaming','video_unprepare_streaming','video_stop_streaming','msm_video_register']),('camss.c',['camss_get','camss_put','camss_genpd_init','camss_probe']),('camss-vfe.c',['vfe_get','vfe_put','vfe_set_power','vfe_queue_buffer']),('camss-csid-gen2.c',['csid_configure_stream','csid_configure_testgen','csid_testgen_enable']),('camss-csid.c',['csid_set_test_pattern'])]:
 t=(d/filename).read_text()
 for name in names:
  m=re.search(r'\b'+name+r'\([^;{}]*\)\s*\{',t)
  if not m:print('MISSING',filename,name);continue
  start=t.rfind('\n\n',0,m.start())+2;brace=t.index('{',m.start());end=brace+1;level=1
  while level:level+=(t[end]=='{')-(t[end]=='}');end+=1
  print(filename,t[start:end][:9000])
 for line in t.splitlines():
  if any(q in line for q in ['parent_dev_ops','vb2_dma','mem_ops','sm8150',' testgen_']):print(filename,line)
t=(k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts').read_text();a=t.index('&camss {');print(t[a:a+350])
