from pathlib import Path
import runpy,hashlib
r=Path('/mnt/e/RealmeX2Pro edk2');runpy.run_path(str(r/'reference/kernel122/ensure-rootfs-volume.py'));k=Path('/home/cy122/pmos-samurai-rootfs122/camera125/kernel')
assert hashlib.sha256((k/'arch/arm64/boot/Image').read_bytes()).hexdigest()=='4bded2cb151f910adc3ccd7c6545f4f2702b9a3a1022d4b9dbbcd5364edcf389'
for name,patterns in [('camss-video.c',['static int video_buf_prepare','static void video_buf_queue','static int video_start_streaming','static const struct vb2_ops']),('camss-csid.c',['static int csid_set_power','static int csid_set_stream','static int csid_init_formats','static int csid_test_pattern']),('camss.c',['static int camss_register_entities','static int camss_init_subdevices'])]:
 text=(k/'drivers/media/platform/qcom/camss'/name).read_text()
 for pattern in patterns:
  start=text.find(pattern)
  if start<0:print('MISSING',name,pattern);continue
  brace=text.index('{',start);end=brace+1;level=1
  while level:level+=(text[end]=='{')-(text[end]=='}');end+=1
  print(name,text[start:end][:12000])
for rel in ['drivers/media/platform/qcom/camss/camss-video.h','arch/arm64/boot/dts/qcom/sm8150-samurai.dts']:
 print(rel,(k/rel).read_text()[:11000])
