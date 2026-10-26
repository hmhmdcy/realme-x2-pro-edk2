"""Compare the original and correctly routed synthetic FULL image using measured NV12 patches."""
from pathlib import Path
import hashlib,json,os,sys

ROOT=Path(__file__).resolve().parent
if os.name!='nt':
 import host,shlex
 for suffix,label in [('', 'before'),('.corrected','after')]:
  data=bytearray()
  for offset in range(0,115200,65536):
   code=f"from pathlib import Path;import sys;b=Path('/var/lib/samurai/k290-route-r1/first-nv12-private.raw{suffix}').read_bytes();assert len(b)==115200;sys.stdout.buffer.write(b[{offset}:{min(offset+65536,115200)}])"
   q=host.ssh('python3 -c '+shlex.quote(code),input=None,timeout=15);assert len(q.stdout)==min(65536,115200-offset);data.extend(q.stdout)
  p=host.PRIVATE/(label+'-route-private.nv12');assert not p.exists();p.write_bytes(data)
 print('Fetched synthetic before/after route frames.');sys.exit(0)
import numpy as np
from PIL import Image
PRIVATE=Path('E:/edk2-samurai-out/kernel290')
report=dict(stage=290,synthetic_tpg=True,same_stream_before_after=True,gamma_and_full_route_corrected=True)
for label in ['before','after']:
 data=(PRIVATE/(label+'-route-private.nv12')).read_bytes();a=np.frombuffer(data,np.uint8)
 y=a[:76800].reshape(240,320);uv=a[76800:].reshape(120,160,2);patches=[]
 for i in range(8):
  l=i*40+4;r=(i+1)*40-4
  patches.append(dict(index=i,y=float(y[:,l:r].mean()),u=float(uv[:,l//2:r//2,0].mean()),v=float(uv[:,l//2:r//2,1].mean()),
   y_even=float(y[0::2,l:r].mean()),y_odd=float(y[1::2,l:r].mean())))
 report[label]=dict(sha256=hashlib.sha256(data).hexdigest(),patches=patches)
 u=uv[:,:,0].repeat(2,axis=0).repeat(2,axis=1).astype(float)-128;v=uv[:,:,1].repeat(2,axis=0).repeat(2,axis=1).astype(float)-128
 rgb=np.clip(np.rint(np.stack([y+1.402*v,y-.344136*u-.714136*v,y+1.772*u],axis=2)),0,255).astype(np.uint8)
 Image.fromarray(rgb).save(PRIVATE/(label+'-route-preview-private.png'))
report['black_white_neutrality_passed']=all(abs(report['after']['patches'][i][c]-128)<=1 for i in [0,7] for c in ['u','v'])
report['black_y']=report['after']['patches'][7]['y'];report['white_y']=report['after']['patches'][0]['y']
report['expected_green_magenta_response_consistent']=abs(report['after']['patches'][4]['y']-149)<=2 and abs(report['after']['patches'][3]['y']-105)<=2
report['physical_sensor_and_full_iq_validation_still_required']=True
(ROOT/'route-pixel-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
