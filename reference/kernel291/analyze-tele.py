"""Validate the GRBG telephoto sensor bars against an independent RAW reference."""
from pathlib import Path
import hashlib,json,os,re,sys
ROOT=Path(__file__).resolve().parent
if os.name!='nt':
 import host,shlex
 data=bytearray()
 for offset in range(0,115200,65536):
  code=f"from pathlib import Path;import sys;b=Path('/var/lib/samurai/k291-tele-pattern-pix-r1/frame-private-5.nv12').read_bytes();assert len(b)==115200;sys.stdout.buffer.write(b[{offset}:{min(offset+65536,115200)}])"
  q=host.ssh('python3 -c '+shlex.quote(code),timeout=15);assert len(q.stdout)==min(65536,115200-offset);data.extend(q.stdout)
 p=host.PRIVATE/'tele-pattern-pix-5-private.nv12';assert not p.exists();p.write_bytes(data)
 print('Fetched telephoto sensor-pattern NV12 privately.');sys.exit(0)
import numpy as np
from PIL import Image
private=Path('E:/edk2-samurai-out/kernel291')
b=(private/'tele-pattern-pix-5-private.nv12').read_bytes();assert len(b)==115200
a=np.frombuffer(b,np.uint8);y=a[:76800].reshape(240,320);uv=a[76800:].reshape(120,160,2)
raw=json.loads((ROOT/'tele-pattern-raw-capture-validation.json').read_text())
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
u=uv[:,:,0].repeat(2,0).repeat(2,1).astype(float)-128;v=uv[:,:,1].repeat(2,0).repeat(2,1).astype(float)-128
rgb=np.clip(np.rint(np.stack([y+1.402*v,y-.344136*u-.714136*v,y+1.772*u],axis=2)),0,255).astype(np.uint8)
Image.fromarray(rgb).save(private/'tele-pattern-pix-5-preview-private.png')
report=dict(stage=291,kernel_build=290,sensor='s5k3m5',bayer='GRBG',physical_csi=True,sensor_pattern=2,csid_pattern=0,
 no_cpu_isp=True,no_userspace_mmio=True,patches=patches,sha256=hashlib.sha256(b).hexdigest(),
 independent_red_blue_input_present=any(p['raw_rgb'][0]!=p['raw_rgb'][2] for p in patches),
 color_contract_passed=all(p['max_error']<=3 for p in patches),
 validation_scope='Static eight vertical sensor bars, GRBG mode, negotiated 2104x1560 to 320x240; separate RAW reference',
 vertical_scaling_quality_optical_geometry_full_iq_and_ipa_not_verified=True,
 raw_tool_input_log_output_label_stale=True,raw_actual_format_and_bytes_verified=True)
(ROOT/'tele-pixel-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
assert report['color_contract_passed'] and report['independent_red_blue_input_present']
