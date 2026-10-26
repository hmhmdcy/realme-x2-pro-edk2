"""Measure before/after synthetic NV12 patches, retaining full images privately."""
from pathlib import Path
import hashlib,json,os,sys

ROOT=Path(__file__).resolve().parent
if os.name!='nt':
 import host,shlex
 for suffix,label in [('', 'before'),('.corrected','after')]:
  data=bytearray()
  for offset in range(0,115200,65536):
   code=f"from pathlib import Path;import sys;b=Path('/var/lib/samurai/k289-gamma-r1/first-nv12-private.raw{suffix}').read_bytes();assert len(b)==115200;sys.stdout.buffer.write(b[{offset}:{min(offset+65536,115200)}])"
   q=host.ssh('python3 -c '+shlex.quote(code),timeout=15);assert len(q.stdout)==min(65536,115200-offset);data.extend(q.stdout)
  p=host.PRIVATE/(label+'-gamma-upload-private.nv12');assert not p.exists();p.write_bytes(data)
 print('Fetched before/after synthetic hardware frames.');sys.exit(0)
import numpy as np
from PIL import Image
PRIVATE=Path('E:/edk2-samurai-out/kernel289')
report=dict(stage=289,same_stream_before_and_after=True,standard_curve_unchanged=True,synthetic_tpg=True)
for label in ['before','after']:
 data=(PRIVATE/(label+'-gamma-upload-private.nv12')).read_bytes();a=np.frombuffer(data,np.uint8)
 y=a[:76800].reshape(240,320);uv=a[76800:].reshape(120,160,2)
 patches=[]
 for i in range(8):
  left=i*40+4;right=(i+1)*40-4
  patches.append(dict(index=i,y=float(y[:,left:right].mean()),u=float(uv[:,left//2:right//2,0].mean()),v=float(uv[:,left//2:right//2,1].mean()),
   y_even=float(y[0::2,left:right].mean()),y_odd=float(y[1::2,left:right].mean())))
 report[label]=dict(sha256=hashlib.sha256(data).hexdigest(),patches=patches)
 u=uv[:,:,0].repeat(2,axis=0).repeat(2,axis=1).astype(float)-128
 v=uv[:,:,1].repeat(2,axis=0).repeat(2,axis=1).astype(float)-128
 rgb=np.clip(np.rint(np.stack([y+1.402*v,y-.344136*u-.714136*v,y+1.772*u],axis=2)),0,255).astype(np.uint8)
 Image.fromarray(rgb).save(PRIVATE/(label+'-gamma-upload-preview-private.png'))
report['white_black_chroma_neutral_after']=all(abs(report['after']['patches'][i][c]-128)<=1 for i in [0,7] for c in ['u','v'])
report['color_quality_complete']=False
(ROOT/'gamma-upload-pixel-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
