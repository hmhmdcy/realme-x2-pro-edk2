"""Measure standard WB parameter effects, snapshotting, disable and reopen behavior."""
from pathlib import Path
import hashlib,json,os,re,sys
ROOT=Path(__file__).resolve().parent
if os.name!='nt':
 import host,shlex
 for n in range(8,81,9):
  data=bytearray()
  for offset in range(0,115200,65536):
   code=f"from pathlib import Path;import sys;b=Path('/var/lib/samurai/k292-wb-params-r1/frame-private-{n}.nv12').read_bytes();assert len(b)==115200;sys.stdout.buffer.write(b[{offset}:{min(offset+65536,115200)}])"
   q=host.ssh('python3 -c '+shlex.quote(code),timeout=15);assert len(q.stdout)==min(65536,115200-offset);data.extend(q.stdout)
  p=host.PRIVATE/f'wb-params-{n}-private.nv12';assert not p.exists();p.write_bytes(data)
 print('Fetched nine hardware WB phase frames privately.');sys.exit(0)
import numpy as np
from PIL import Image
private=Path('E:/edk2-samurai-out/kernel292')
raw=json.loads((ROOT.parent/'kernel291/tele-pixel-validation.json').read_text())
rgb=np.array([p['raw_rgb'] for p in raw['patches']]);assert rgb.shape==(8,3)
names=['initial_unity_snapshot','red_quarter','blue_quarter','green_quarter','disable','disabled_value_update','enable_red_quarter','params_stopped_image_continues','image_reopen_defaults']
gains=np.ones((9,3));gains[1,0]=.25;gains[2,2]=.25;gains[3,1]=.25;gains[6:8,0]=.25
matrix=np.array([[.299,.587,.114],[-.168736,-.331264,.5],[.5,-.418688,-.081312]])
phases=[]
for phase,n in enumerate(range(8,81,9)):
 b=(private/f'wb-params-{n}-private.nv12').read_bytes();a=np.frombuffer(b,np.uint8);y=a[:76800].reshape(240,320);uv=a[76800:].reshape(120,160,2)
 linear=np.clip(rgb*gains[phase],0,1);encoded=np.where(linear<=.0031308,12.92*linear,1.055*np.power(linear,1/2.4)-.055)*255
 expected=np.clip(encoded@matrix.T+np.array([0,128,128]),0,255);patches=[]
 for i in range(8):
  left=i*40+8;right=(i+1)*40-8
  actual=np.array([y[8:-8,left:right].mean(),uv[4:-4,left//2:right//2,0].mean(),uv[4:-4,left//2:right//2,1].mean()])
  patches.append(dict(index=i,expected_yuv=expected[i].tolist(),actual_yuv=actual.tolist(),max_error=float(abs(expected[i]-actual).max())))
 u=uv[:,:,0].repeat(2,0).repeat(2,1).astype(float)-128;v=uv[:,:,1].repeat(2,0).repeat(2,1).astype(float)-128
 preview=np.clip(np.rint(np.stack([y+1.402*v,y-.344136*u-.714136*v,y+1.772*u],axis=2)),0,255).astype(np.uint8)
 Image.fromarray(preview).save(private/f'wb-params-{n}-preview-private.png')
 phases.append(dict(phase=phase,name=names[phase],frame=n,gains_rgb=gains[phase].tolist(),sha256=hashlib.sha256(b).hexdigest(),max_error=max(p['max_error'] for p in patches),patches=patches))
report=dict(stage=292,kernel_build=292,sensor='s5k3m5',standard_typed_metadata=True,no_userspace_mmio=True,no_cpu_isp=True,
 phases=phases,all_phase_color_contracts_passed=all(p['max_error']<=4 for p in phases),
 snapshot_after_qbuf_verified=all(p['max_error']<=4 for p in phases[:7]),
 params_streamoff_preserves_image_state=phases[7]['max_error']<=4,
 image_reopen_resets_defaults=phases[8]['max_error']<=4,
 black_level_statistics_ipa_and_full_iq_incomplete=True,
 raw_reference='kernel291 tele sensor pattern, unchanged sensor driver and mode')
(ROOT/'wb-params-pixel-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(stage=292,phases=[{k:v for k,v in p.items() if k!='patches'} for p in phases],passed=report['all_phase_color_contracts_passed']),indent=2))
assert report['all_phase_color_contracts_passed']
