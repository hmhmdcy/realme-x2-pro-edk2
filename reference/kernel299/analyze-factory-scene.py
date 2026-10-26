"""Measure scene comparisons without treating them as dark or color calibration."""
from pathlib import Path
import hashlib,json,os,sys
HERE=Path(__file__).resolve().parent
if os.name!='nt':
 import host,shlex
 assert json.loads((HERE/'factory-scene-capture-validation.json').read_text())['passed']
 for frame in range(8,54,9):
  command=f"from pathlib import Path;import sys;b=Path('/var/lib/samurai/k299-factory-scene/frame-private-{frame}.nv12').read_bytes();assert len(b)==115200;sys.stdout.buffer.write(b)"
  q=host.ssh('python3 -c '+shlex.quote(command),timeout=15);assert len(q.stdout)==115200
  p=host.PRIVATE/f'scene-{frame}-private.nv12';assert not p.exists();p.write_bytes(q.stdout)
 print('Fetched six private IMX319 hardware scene comparisons.');sys.exit(0)
import numpy as np
from PIL import Image
P=Path('E:/edk2-samurai-out/kernel299');capture=json.loads((HERE/'factory-scene-capture-validation.json').read_text());rows=[]
names=['uncorrected_black_scene_wb','factory_black_scene_wb','factory_black_normalized_scene_wb','scene_black_normalized_scene_wb','wb_blc_bypassed','factory_black_normalized_reenabled']
for phase,frame in enumerate(range(8,54,9)):
 b=(P/f'scene-{frame}-private.nv12').read_bytes();a=np.frombuffer(b,np.uint8);y=a[:76800].reshape(240,320).astype(float);uv=a[76800:].reshape(120,160,2).astype(float)
 u=uv[:,:,0].repeat(2,0).repeat(2,1)-128;v=uv[:,:,1].repeat(2,0).repeat(2,1)-128
 rgb=np.clip(np.stack([y+1.402*v,y-.344136*u-.714136*v,y+1.772*u],2),0,255);mean=rgb.mean((0,1))
 Image.fromarray(np.rint(rgb).astype(np.uint8)).save(P/f'scene-{frame}-preview-private.png')
 stats=[r for r in capture['statistics'] if r['phase']==phase and r['frame']%9>=4]
 rows.append(dict(phase=phase,name=names[phase],frame=frame,mean_y=float(y.mean()),rgb_mean=mean.tolist(),green_over_red_blue=float(mean[1]/((mean[0]+mean[2])/2)),luma_percentiles=np.percentile(y,[1,10,50,90,99]).tolist(),high_clip_fraction=float((y>=254).mean()),histogram_mean=float(np.mean([r['weighted']/r['sum'] for r in stats])),histogram_population=sorted(set(r['sum'] for r in stats)),sha256=hashlib.sha256(b).hexdigest()))
report=dict(stage=299,kernel_build=298,sensor='imx319',sensor_pattern=0,csid_pattern=0,analogue_gain_code=768,exposure_code=3000,
 same_exposure_gain_and_fixed_provisional_color_gains=True,provisional_wb_is_not_factory_awb=True,phases=rows,
 factory_subtraction_reduces_black_pedestal=rows[1]['mean_y']<rows[0]['mean_y'],explicit_normalization_increases_output=rows[2]['mean_y']>rows[1]['mean_y'],
 scene64_reference_is_darker_than_factory60=rows[3]['mean_y']<rows[2]['mean_y'],reenabled_mean_y_difference=abs(rows[5]['mean_y']-rows[2]['mean_y']),
 full_color_calibration_not_claimed=True,no_dark_calibration=True,factory_iq_pipeline_not_recreated=True,no_installed_tuning_change=True)
(HERE/'factory-scene-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
assert report['factory_subtraction_reduces_black_pedestal'] and report['explicit_normalization_increases_output'] and report['scene64_reference_is_darker_than_factory60']
