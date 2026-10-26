"""Compare the physical hardware scene experiment; estimates are not calibration."""
from pathlib import Path
import hashlib,json,os,sys
HERE=Path(__file__).resolve().parent
if os.name!='nt':
 import host,shlex
 assert json.loads((HERE/'scene-capture-validation.json').read_text())['passed']
 for n in [8,17,26,35,44,62,80]:
  data=bytearray()
  for offset in range(0,115200,65536):
   end=min(offset+65536,115200)
   code=f"from pathlib import Path;import sys;b=Path('/var/lib/samurai/k298-scene/frame-private-{n}.nv12').read_bytes();assert len(b)==115200;sys.stdout.buffer.write(b[{offset}:{end}])"
   q=host.ssh('python3 -c '+shlex.quote(code),timeout=15);assert len(q.stdout)==end-offset;data.extend(q.stdout)
  p=host.PRIVATE/f'scene-{n}-private.nv12';assert not p.exists();p.write_bytes(data)
 print('Fetched seven private physical hardware scene frames.');sys.exit(0)
import numpy as np
from PIL import Image
P=Path('E:/edk2-samurai-out/kernel298');rows=[]
for n,label in [(8,'neutral_no_blc_2x'),(17,'blc_only_2x'),(26,'blc_scene_wb_2x'),(35,'blc_scene_wb_4x'),(44,'bypass_blc_wb_4x'),(62,'reenabled_blc_scene_wb_4x'),(80,'reopen_neutral_4x')]:
 b=(P/f'scene-{n}-private.nv12').read_bytes();a=np.frombuffer(b,np.uint8)
 y=a[:76800].reshape(240,320).astype(float);uv=a[76800:].reshape(120,160,2).astype(float)
 u=uv[:,:,0].repeat(2,0).repeat(2,1)-128;v=uv[:,:,1].repeat(2,0).repeat(2,1)-128
 rgb=np.clip(np.stack([y+1.402*v,y-.344136*u-.714136*v,y+1.772*u],2),0,255)
 mean=rgb.mean((0,1));im=Image.fromarray(np.rint(rgb).astype(np.uint8));im.save(P/f'scene-{n}-preview-private.png')
 rows.append(dict(frame=n,name=label,mean_y=float(y.mean()),rgb_mean=mean.tolist(),green_over_red_blue_mean=float(mean[1]/((mean[0]+mean[2])/2)),chroma_mean=uv.mean((0,1)).tolist(),luma_percentiles=np.percentile(y,[1,10,50,90,99]).tolist(),luma_clipped_high_fraction=float((y>=254).mean()),sha256=hashlib.sha256(b).hexdigest()))
report=dict(stage=298,sensor='imx319',mode=[1632,1224],output=[320,240],sensor_pattern=0,csid_pattern=0,
 physical_hardware_nv12=True,no_cpu_processing_before_capture=True,no_userspace_mmio=True,
 phases=rows,black_only_reduces_brightness=rows[1]['mean_y']<rows[0]['mean_y'],
 provisional_wb_reduces_global_green_excess=abs(rows[2]['green_over_red_blue_mean']-1)<abs(rows[1]['green_over_red_blue_mean']-1),
 analogue_gain_increases_brightness=rows[3]['mean_y']>rows[2]['mean_y'],
 global_neutrality_is_not_color_accuracy=True,uncontrolled_scene=True,covered_lens_dark_calibration_completed=False,
 scene_estimates_not_installed_as_tuning=True,full_iq_accepted=False,hardware_pipeline_ipa_integrated=False)
(HERE/'scene-analysis-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
assert report['black_only_reduces_brightness'] and report['provisional_wb_reduces_global_green_excess'] and report['analogue_gain_increases_brightness']
