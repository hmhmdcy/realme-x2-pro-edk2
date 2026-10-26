"""Offline optical comparison; pixels remain in the private output directory."""
from pathlib import Path
import hashlib,json
import numpy as np
from PIL import Image,ImageFilter
R=Path(__file__).resolve().parent
P=Path('E:/edk2-samurai-out/kernel276')
proof=json.loads((R/'standard-focus-validation.json').read_text())
rows=[]
for row in proof['runs']:
 p=P/('standard-focus-'+str(row['index'])+'-'+str(row['position'])+'-private.jpg')
 assert hashlib.sha256(p.read_bytes()).hexdigest()==row['jpeg']['sha256']
 im=Image.open(p);assert im.size==(1280,960)
 green=im.getchannel('G');regions={}
 for name,box in [('curtain',(944,80,1260,640)),('cabinet',(32,640,880,920)),('boundary',(48,480,848,640))]:
  crop=green.crop(box);scores={}
  for radius in [0,2,4,8]:
   a=np.asarray(crop.filter(ImageFilter.GaussianBlur(radius)),dtype=float)
   dy,dx=np.gradient(a);energy=float(np.mean(dx*dx+dy*dy));mean=float(a.mean())
   scores[str(radius)]=dict(mean=mean,gradient_energy=energy,normalized_gradient_energy=energy/max(1,mean*mean))
  regions[name]=scores
 a=np.asarray(green.filter(ImageFilter.GaussianBlur(2)),dtype=float);widths=[]
 for x in range(64,832,16):
  profile=a[480:640,x]
  contrast=abs(float(np.median(profile[:20])-np.median(profile[-20:])))
  peak=float(np.max(np.abs(np.diff(profile))))
  if contrast>=8 and peak>0:widths.append(contrast/peak)
 rows.append(dict(index=row['index'],position=row['position'],jpeg_sha256=row['jpeg']['sha256'],regions=regions,
  median_edge_spread_proxy_pixels=float(np.median(widths)) if widths else None,edge_columns=len(widths)))
out=dict(stage=276,rows=rows,standard_v4l2_control_not_raw_i2c=True,
 visual_review_208_vs_880_shows_large_defocus_change=True,return208_recovers_visible_detail=True,
 physical_lens_response_observed=True,position_feedback_not_verified=True,automatic_exposure_was_not_locked=True,
 jpeg_and_statistics_not_same_request=True,center_flat_wall_noise_dominated_metric_not_used_to_claim_af=True,
 focus_distance_calibration_not_completed=True,autofocus_not_complete=True)
(R/'standard-focus-optical-analysis.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps([dict(position=r['position'],edge_spread=r['median_edge_spread_proxy_pixels']) for r in rows]))
