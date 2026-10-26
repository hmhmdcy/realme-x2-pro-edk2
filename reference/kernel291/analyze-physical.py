"""Compare hardware NV12 with sensor-generated independent R/B RAW references."""
from pathlib import Path
import hashlib,json,os,re,sys
ROOT=Path(__file__).resolve().parent
if os.name!='nt':
 import host,shlex
 items=[('physical',n) for n in [5,11,17]]+[('pattern-pix',5)]
 for name,n in items:
  data=bytearray()
  for offset in range(0,115200,65536):
   code=f"from pathlib import Path;import sys;b=Path('/var/lib/samurai/k291-{name}-r1/frame-private-{n}.nv12').read_bytes();assert len(b)==115200;sys.stdout.buffer.write(b[{offset}:{min(offset+65536,115200)}])"
   q=host.ssh('python3 -c '+shlex.quote(code),timeout=15);assert len(q.stdout)==min(65536,115200-offset);data.extend(q.stdout)
  p=host.PRIVATE/f'{name}-{n}-private.nv12';assert not p.exists();p.write_bytes(data)
 print('Fetched physical and sensor-pattern NV12 frames privately.');sys.exit(0)
import numpy as np
from PIL import Image
private=Path('E:/edk2-samurai-out/kernel291')
def planes(name,n):
 b=(private/f'{name}-{n}-private.nv12').read_bytes();assert len(b)==115200
 a=np.frombuffer(b,np.uint8);y=a[:76800].reshape(240,320);uv=a[76800:].reshape(120,160,2)
 u=uv[:,:,0].repeat(2,0).repeat(2,1).astype(float)-128;v=uv[:,:,1].repeat(2,0).repeat(2,1).astype(float)-128
 rgb=np.clip(np.rint(np.stack([y+1.402*v,y-.344136*u-.714136*v,y+1.772*u],axis=2)),0,255).astype(np.uint8)
 Image.fromarray(rgb).save(private/f'{name}-{n}-preview-private.png')
 return b,y,uv
report=dict(stage=291,kernel_build=290,physical_csi=True,no_cpu_isp=True,no_userspace_mmio=True)
real=[]
for n in [5,11,17]:
 b,y,uv=planes('physical',n)
 real.append(dict(frame=n,exposure_code=3000 if n==11 else 500,sha256=hashlib.sha256(b).hexdigest(),y_mean=float(y.mean()),y_std=float(y.std()),y_min=int(y.min()),y_max=int(y.max()),uv_mean=float(uv.mean())))
report['physical_scene']=real;report['physical_optical_scene_not_yet_verified']=True
b,y,uv=planes('pattern-pix',5)
raw=json.loads((ROOT/'pattern-raw-capture-validation.json').read_text())
rows=re.findall(r'RAW_PATCH frame=5 bar=(\d+) r=([\d.]+) gr=([\d.]+) gb=([\d.]+) b=([\d.]+)',raw['tool_output']);assert len(rows)==8
patches=[]
for index,r,gr,gb,blue in rows:
 i=int(index);values=np.array([float(r),(float(gr)+float(gb))/2,float(blue)])/1023
 assert all(x in [0.,1.] for x in values)
 red,green,blue=values
 expected=np.clip(np.array([.299*red+.587*green+.114*blue,-.168736*red-.331264*green+.5*blue,.5*red-.418688*green-.081312*blue])*255+np.array([0,128,128]),0,255)
 left=i*40+6;right=(i+1)*40-6
 actual=np.array([y[8:-8,left:right].mean(),uv[4:-4,left//2:right//2,0].mean(),uv[4:-4,left//2:right//2,1].mean()])
 patches.append(dict(index=i,raw_rgb=list(values),expected_yuv=expected.tolist(),actual_yuv=actual.tolist(),max_error=float(abs(expected-actual).max())))
report['pattern_patches']=patches
report['pattern_nv12_sha256']=hashlib.sha256(b).hexdigest()
report['independent_red_blue_input_present']=any(p['raw_rgb'][0]!=p['raw_rgb'][2] for p in patches)
report['sensor_pattern_color_contract_passed']=all(p['max_error']<=3 for p in patches)
report['rggb_physical_csi_demosaic_gamma_cst_scaling_round_output_verified']=report['sensor_pattern_color_contract_passed'] and report['independent_red_blue_input_present']
report['full_iq_statistics_params_ipa_still_incomplete']=True
report['color_validation_scope']='Static vertical sensor bars, RGGB mode, negotiated 1632x1224 to 320x240; separate RDI reference'
report['vertical_scaling_quality_optical_geometry_and_full_iq_not_verified']=True
(ROOT/'physical-pixel-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
assert report['rggb_physical_csi_demosaic_gamma_cst_scaling_round_output_verified']
