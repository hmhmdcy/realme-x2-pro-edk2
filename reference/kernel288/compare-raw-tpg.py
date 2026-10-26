"""Compare synthetic RAW color patches with corresponding hardware NV12 patches."""
from pathlib import Path
import hashlib,json,os,sys

ROOT=Path(__file__).resolve().parent
if os.name!='nt':
 import host,shlex
 result=bytearray()
 for offset in range(0,96000,65536):
  code=f"from pathlib import Path;import sys;b=Path('/var/lib/samurai/k288-rdi-control-r1/first-rdi-private.raw').read_bytes();assert len(b)==96000;sys.stdout.buffer.write(b[{offset}:{min(offset+65536,96000)}])"
  q=host.ssh('python3 -c '+shlex.quote(code),timeout=15);assert len(q.stdout)==min(65536,96000-offset);result.extend(q.stdout)
 p=host.PRIVATE/'tpg-rdi-reference-private.raw';assert not p.exists();p.write_bytes(result);print('Fetched synthetic RAW reference.');sys.exit(0)
import numpy as np
private=Path('E:/edk2-samurai-out/kernel288')
data=(private/'tpg-rdi-reference-private.raw').read_bytes()
packed=np.frombuffer(data,dtype=np.uint8).reshape(240,80,5).astype(np.uint16)
raw=np.empty((240,320),dtype=np.uint16)
for i in range(4):raw[:,i::4]=(packed[:,:,i]<<2)|((packed[:,:,4]>>(2*i))&3)
nv12=np.frombuffer((private/'first-hardware-tpg-nv12-private.raw').read_bytes(),dtype=np.uint8)
y=nv12[:76800].reshape(240,320);uv=nv12[76800:].reshape(120,160,2)
rows=[]
for i in range(8):
 a=i*40+4;b=(i+1)*40-4
 crop=raw[:,a:b]
 cfa={n:float(crop[dy::2,dx::2].mean()) for n,dy,dx in [('Gr',0,0),('R',0,1),('B',1,0),('Gb',1,1)]}
 rows.append(dict(index=i,raw_cfa_means=cfa,y_mean=float(y[:,a:b].mean()),u_mean=float(uv[:,a//2:b//2,0].mean()),v_mean=float(uv[:,a//2:b//2,1].mean()),
                  y_even_mean=float(y[0::2,a:b].mean()),y_odd_mean=float(y[1::2,a:b].mean())))
report=dict(stage=288,raw_reference_sha256=hashlib.sha256(data).hexdigest(),raw_min=int(raw.min()),raw_max=int(raw.max()),patches=rows,
            raw_and_nv12_separate_synthetic_captures=True,hardware_color_order_not_yet_proven=True)
(ROOT/'raw-nv12-tpg-comparison.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
