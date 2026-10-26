"""Preserve and measure the fresh real-scene exposure response on actual290."""
from pathlib import Path
import hashlib,json,os,sys
ROOT=Path(__file__).resolve().parent
if os.name!='nt':
 import host,shlex
 for n in [5,11,17]:
  data=bytearray()
  for offset in range(0,115200,65536):
   code=f"from pathlib import Path;import sys;b=Path('/var/lib/samurai/k295-optical-r1/frame-private-{n}.nv12').read_bytes();assert len(b)==115200;sys.stdout.buffer.write(b[{offset}:{min(offset+65536,115200)}])"
   q=host.ssh('python3 -c '+shlex.quote(code),timeout=15);assert len(q.stdout)==min(65536,115200-offset);data.extend(q.stdout)
  p=host.PRIVATE/f'optical-{n}-private.nv12';assert not p.exists();p.write_bytes(data)
 print('Fetched fresh physical scene frames privately.');sys.exit(0)
import numpy as np
from PIL import Image
private=Path('E:/edk2-samurai-out/kernel295');rows=[]
for n in [5,11,17]:
 b=(private/f'optical-{n}-private.nv12').read_bytes();a=np.frombuffer(b,np.uint8);y=a[:76800].reshape(240,320);uv=a[76800:].reshape(120,160,2)
 u=uv[:,:,0].repeat(2,0).repeat(2,1).astype(float)-128;v=uv[:,:,1].repeat(2,0).repeat(2,1).astype(float)-128
 rgb=np.clip(np.rint(np.stack([y+1.402*v,y-.344136*u-.714136*v,y+1.772*u],axis=2)),0,255).astype(np.uint8)
 Image.fromarray(rgb).save(private/f'optical-{n}-preview-private.png')
 rows.append(dict(frame=n,exposure_code=3000 if n==11 else 500,y_mean=float(y.mean()),y_std=float(y.std()),y_min=int(y.min()),y_max=int(y.max()),sha256=hashlib.sha256(b).hexdigest()))
report=dict(stage=295,actual_kernel_build=295,sensor='imx319',sensor_and_csid_tpg_disabled=True,hardware_full_nv12=True,frames=rows,
 exposure_response_and_return_passed=rows[1]['y_mean']>rows[0]['y_mean']+5 and abs(rows[2]['y_mean']-rows[0]['y_mean'])<1,
 user_confirmed_normal_scene=True,visual_review_pending=True,black_level_awb_and_full_iq_not_calibrated=True)
(ROOT/'optical-pixel-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
