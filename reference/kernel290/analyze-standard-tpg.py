"""Measure the production driver TPG frame; keep pixels in private storage."""
from pathlib import Path
import hashlib,json,os,sys

ROOT=Path(__file__).resolve().parent
if os.name!='nt':
 import host,shlex
 data=bytearray()
 for offset in range(0,115200,65536):
  code=f"from pathlib import Path;import sys;b=Path('/var/lib/samurai/k290-standard-tpg-r1/first-nv12-private.raw').read_bytes();assert len(b)==115200;sys.stdout.buffer.write(b[{offset}:{min(offset+65536,115200)}])"
  q=host.ssh('python3 -c '+shlex.quote(code),timeout=15)
  assert len(q.stdout)==min(65536,115200-offset);data.extend(q.stdout)
 p=host.PRIVATE/'standard-tpg-private.nv12';assert not p.exists();p.write_bytes(data)
 print('Fetched production-driver synthetic TPG frame.');sys.exit(0)
import numpy as np
from PIL import Image
private=Path('E:/edk2-samurai-out/kernel290')
data=(private/'standard-tpg-private.nv12').read_bytes();assert len(data)==115200
a=np.frombuffer(data,np.uint8);y=a[:76800].reshape(240,320);uv=a[76800:].reshape(120,160,2)
patches=[]
for i in range(8):
 l=i*40+4;r=(i+1)*40-4
 patches.append(dict(index=i,y=float(y[:,l:r].mean()),u=float(uv[:,l//2:r//2,0].mean()),v=float(uv[:,l//2:r//2,1].mean())))
neutral=all(abs(patches[i][c]-128)<=1 for i in [0,7] for c in ['u','v'])
levels=patches[0]['y']==255 and patches[7]['y']==0
colours=abs(patches[4]['y']-149)<=2 and abs(patches[3]['y']-105)<=2
report=dict(stage=290,kernel_build=290,synthetic_tpg=True,standard_mc_v4l2_only=True,
 no_userspace_mmio=True,no_physical_dphy_history_workaround=True,
 sha256=hashlib.sha256(data).hexdigest(),patches=patches,
 black_white_neutrality_passed=neutral,black_white_levels_passed=levels,
 green_magenta_response_passed=colours,passed=neutral and levels and colours,
 independent_red_blue_validation_required=True,physical_sensor_quality_not_claimed=True)
u=uv[:,:,0].repeat(2,0).repeat(2,1).astype(float)-128
v=uv[:,:,1].repeat(2,0).repeat(2,1).astype(float)-128
rgb=np.clip(np.rint(np.stack([y+1.402*v,y-.344136*u-.714136*v,y+1.772*u],axis=2)),0,255).astype(np.uint8)
Image.fromarray(rgb).save(private/'standard-tpg-preview-private.png')
(ROOT/'standard-tpg-pixel-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2));assert report['passed']
