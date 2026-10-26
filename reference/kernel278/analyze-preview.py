"""Offline bounded visual evidence; private scene pixels are not copied into sources."""
from pathlib import Path
import hashlib,json
import numpy as np
from PIL import Image,ImageFilter
R=Path(__file__).resolve().parent;p=Path('E:/edk2-samurai-out/kernel278/af-selected-preview-private.jpg')
proof=json.loads((R/'af-selected-preview-validation.json').read_text());assert hashlib.sha256(p.read_bytes()).hexdigest()==proof['jpeg']['sha256']
im=Image.open(p);assert im.size==(1280,960);green=im.getchannel('G');a=np.asarray(green.filter(ImageFilter.GaussianBlur(2)),dtype=float);widths=[]
for x in range(64,832,16):
 profile=a[480:640,x];contrast=abs(float(np.median(profile[:20])-np.median(profile[-20:])));peak=float(np.max(np.abs(np.diff(profile))))
 if contrast>=8 and peak>0:widths.append(contrast/peak)
d=dict(stage=278,jpeg_sha256=proof['jpeg']['sha256'],width=im.width,height=im.height,cached_lens_position=proof['cached_position'],
 visual_review_scene_and_curtain_pattern_recognizable=True,noise_colour_and_global_softness_still_visible=True,
 median_edge_spread_proxy_pixels=float(np.median(widths)) if widths else None,edge_columns=len(widths),
 different_session_from_af_request=True,not_a_distance_or_mtf_calibration=True,no_factory_quality_claim=True,private_pixels_not_in_sources=True)
(R/'af-selected-preview-optical-analysis.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
