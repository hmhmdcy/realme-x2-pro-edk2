"""Fetch the synthetic hardware NV12 frame and inspect actual pixel content."""
from pathlib import Path
import hashlib,json,os,sys

ROOT=Path(__file__).resolve().parent
remote='/var/lib/samurai/k288-tpg-r3/first-nv12-private.raw'
if os.name!='nt':
 import host,shlex
 source=bytearray()
 for offset in range(0,115200,65536):
  code=f"from pathlib import Path;import sys;b=Path({remote!r}).read_bytes();assert len(b)==115200;sys.stdout.buffer.write(b[{offset}:{min(offset+65536,115200)}])"
  q=host.ssh('python3 -c '+shlex.quote(code),timeout=15)
  assert len(q.stdout)==min(65536,115200-offset);source.extend(q.stdout)
 raw=host.PRIVATE/'first-hardware-tpg-nv12-private.raw';assert not raw.exists();raw.write_bytes(source)
 print('Fetched 115200 synthetic NV12 bytes; analyze with the bundled Windows image runtime.')
 sys.exit(0)
import numpy as np
from PIL import Image
private=Path('E:/edk2-samurai-out/kernel288')
source=(private/'first-hardware-tpg-nv12-private.raw').read_bytes()
arr=np.frombuffer(source,dtype=np.uint8)
y=arr[:320*240].reshape(240,320)
uv=arr[320*240:].reshape(120,160,2)
u=uv[:,:,0].repeat(2,axis=0).repeat(2,axis=1).astype(float)-128
v=uv[:,:,1].repeat(2,axis=0).repeat(2,axis=1).astype(float)-128
rgb=np.stack([y+1.402*v,y-.344136*u-.714136*v,y+1.772*u],axis=2)
rgb=np.clip(np.round(rgb),0,255).astype(np.uint8)
preview=private/'first-hardware-tpg-preview-private.png';Image.fromarray(rgb).save(preview)
def stats(a):return dict(min=int(a.min()),max=int(a.max()),mean=float(a.mean()),std=float(a.std()),unique_values=int(len(np.unique(a))))
bars=[]
for x in range(8):
 ys=y[:,x*40:(x+1)*40]
 bars.append(dict(index=x,y_mean=float(ys.mean()),rgb_mean=[float(v) for v in rgb[:,x*40:(x+1)*40].mean(axis=(0,1))]))
report=dict(stage=288,synthetic_internal_tpg=True,hardware_nv12_bytes=len(source),sha256=hashlib.sha256(source).hexdigest(),
            y=stats(y),u=stats(uv[:,:,0]),v=stats(uv[:,:,1]),vertical_eighths=bars,
            preview_conversion='BT.601 full-range NV12 to RGB for display only',
            no_cpu_isp_used_to_produce_captured_nv12=True,calibration_and_color_correctness_not_claimed=True)
(ROOT/'tpg-pixel-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
print(str(preview))
