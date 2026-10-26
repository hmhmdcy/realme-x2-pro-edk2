"""Measure the main camera's actual factory-mesh effect on its internal bars."""
from pathlib import Path
import hashlib,json,math,struct,sys
import numpy as np
HERE=Path(__file__).resolve().parent;P=Path('E:/edk2-samurai-out/kernel325');ns={'math':math,'struct':struct}
run=sys.argv[1] if len(sys.argv)>1 else 'r3'
s=(HERE.parent/'kernel319/check-factory-resampling.py').read_text();exec(s[s.index('def geometry'):s.index('\ncases=')],ns)
s=(HERE.parent/'kernel322/assemble-profile.py').read_text();exec(s[s.index('CHANNELS ='):s.index('\ndef main')],ns)
def read(name,h):
 raw=(P/('images-'+run)/(name+'-private.nv12')).read_bytes();assert len(raw)==320*h*3//2
 a=np.frombuffer(raw,np.uint8);y=a[:320*h].reshape(h,320).astype(float);uv=a[320*h:].reshape(h//2,160,2).repeat(2,0).repeat(2,1).astype(float)
 return np.dstack((y,uv)),hashlib.sha256(raw).hexdigest()
def sample(m,tx,ty):
 ix=np.floor(tx).astype(int);iy=np.floor(ty).astype(int);fx=tx-ix;fy=ty-iy
 def v(dx,dy):return m[np.clip(iy+dy,0,12),np.clip(ix+dx,0,16)]
 return (v(0,0)*(1-fx)+v(1,0)*fx)*(1-fy)+(v(0,1)*(1-fx)+v(1,1)*fx)*fy
f32=lambda v:struct.unpack('<f',struct.pack('<f',v))[0]
matrix=np.array([[.299,.587,.114],[-.168736,-.331264,.5],[.5,-.418688,-.081312]]);rows=[]
observation=json.loads((P/('install-'+run+'-observation.json')).read_text())
for tag,w,h,first in [('4x3',4608,3456,[16,8]),('16x9',4608,2592,[16,440])]:
 oh=240 if tag=='4x3' else 180;base,base_sha=read('s5kgw1-off-'+tag,oh)
 y,x=np.indices((oh,320));mask=(x>=8)&(x<312)&(y>=8)&(y<oh-8)
 edges=np.zeros((oh,320),dtype=bool);edges[:,1:]=np.max(abs(np.diff(base,axis=1)),axis=2)>4
 for shift in range(-6,7):mask &= ~np.roll(edges,shift,axis=1)
 resets=np.flatnonzero(np.median(abs(np.diff(base[:,:,0],axis=0)),axis=1)>8)+1
 for row in resets:mask[abs(y-row)<=3]=False
 rgb=np.clip((base-np.array([0,128,128]))@np.linalg.inv(matrix).T/255,0,1);linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
 grid=ns['geometry'](w,h);cw,ch,ox,oy,level=grid;tx=((x+.5)*(w/2)/320+ox)/cw;ty=((y+.5)*(h/2)/oh+oy)/ch
 for variant in ['qtech_s5kgw1','sunny_s5kgw1']:
  root=next(r for r in json.loads((P.parent/'kernel324'/(variant+'-trees-private.json')).read_text()) if r['uid']==25);gains,_=ns['assemble'](root,100.,6500.,led_index=0)
  meshes=[]
  for c in ['r','gr','gb','b']:
   values=ns['predict']([f32(v) for v in gains[c]],grid,[4639,3471,*first,2,2]);meshes.append(np.array([math.floor(v*1024+.5)/1024 for v in values]).reshape(13,17))
  gain=np.dstack([sample(meshes[0],tx,ty),sample((meshes[1]+meshes[2])/2,tx,ty),sample(meshes[3],tx,ty)])
  corrected=np.clip(linear*gain,0,1);encoded=np.where(corrected<=.0031308,12.92*corrected,1.055*corrected**(1/2.4)-.055)*255
  predicted=np.clip(encoded@matrix.T+np.array([0,128,128]),0,255)
  actual,sha=read(variant+'-'+tag,oh);change=abs(actual-base)[mask];error=abs(actual-predicted)[mask]
  log=observation['logs']['capture-'+variant+'-'+tag+'.log'];assert f'LSC_SENSOR width={w} height={h}' in log and 'LSC_PATTERN_ACTIVE toggled=1' in log
  rows.append(dict(variant=variant,mode=tag,sensor_size=[w,h],output_size=[320,oh],actual_sensor_mode_confirmed=True,sha256=sha,
   differs_from_lsc_disabled=sha!=base_sha,changed_components=int(np.count_nonzero(change)),mean_absolute_yuv_change=float(change.mean()),
   approximate_model_mean_error=float(error.mean()),approximate_model_p99_error=float(np.quantile(error,.99)),approximate_model_max_error=float(error.max()),compared_pixels=int(mask.sum()),excluded_baseline_reset_rows=resets.tolist()))
report=dict(stage=325,run=run,cases=rows,actual_installed_ipa_to_isp=True,internal_sensor_pattern='Shade Color Bars' if run=='r3' else 'Color Bars',
 factory_profile_effect_observed=all(r['differs_from_lsc_disabled'] for r in rows),individual_values_applied=False,
 supplier_binding_verified=False,normal_light_optical_calibration=False,
 model_limit='Independent mesh resampling, bilinear spatial and Bayer approximation, NV12-inverted baseline; clipping limits identification',
 passed=all(r['differs_from_lsc_disabled'] for r in rows))
(HERE/'main-image-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
