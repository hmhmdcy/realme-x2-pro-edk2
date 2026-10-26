"""Quantify two front modes and compare with the retained independent mesh model."""
from pathlib import Path
import hashlib,json,math,struct
import numpy as np
HERE=Path(__file__).resolve().parent;P=Path('E:/edk2-samurai-out/kernel324')
ns={'math':math,'struct':struct}
s=(HERE.parent/'kernel319/check-factory-resampling.py').read_text();exec(s[s.index('def geometry'):s.index('\ncases=')],ns)
s=(HERE.parent/'kernel322/assemble-profile.py').read_text();exec(s[s.index('CHANNELS ='):s.index('\ndef main')],ns)
root=next(r for r in json.loads((P/'sunny_imx471-trees-private.json').read_text()) if r['uid']==25)
gains,_=ns['assemble'](root,100.,6500.,led_index=0)
f32=lambda v:struct.unpack('<f',struct.pack('<f',v))[0]
def read(name,h):
 raw=(P/'capture-r3'/(name+'-private.nv12')).read_bytes();assert len(raw)==320*h*3//2
 a=np.frombuffer(raw,np.uint8);y=a[:320*h].reshape(h,320).astype(float)
 uv=a[320*h:].reshape(h//2,160,2).repeat(2,0).repeat(2,1).astype(float)
 return np.dstack((y,uv)),hashlib.sha256(raw).hexdigest()
def sample(m,tx,ty):
 ix=np.floor(tx).astype(int);iy=np.floor(ty).astype(int);fx=tx-ix;fy=ty-iy
 def v(dx,dy):return m[np.clip(iy+dy,0,12),np.clip(ix+dx,0,16)]
 return (v(0,0)*(1-fx)+v(1,0)*fx)*(1-fy)+(v(0,1)*(1-fx)+v(1,1)*fx)*fy
matrix=np.array([[.299,.587,.114],[-.168736,-.331264,.5],[.5,-.418688,-.081312]]);rows=[]
observation=json.loads((P/'probe-r3-observation.json').read_text())
for tag,w,h,first in [('4x3',2304,1728,[0,0]),('16x9',1928,1088,[200,302])]:
 oh=240 if tag=='4x3' else 180
 base,offsha=read('imx471-off-'+tag,oh);actual,sha=read('sunny_imx471-'+tag,oh);assert sha!=offsha
 log=observation['logs']['capture-sunny_imx471-'+tag+'.log'];assert f'LSC_SENSOR width={w} height={h}' in log
 grid=ns['geometry'](w,h);cw,ch,ox,oy,level=grid
 meshes=[]
 for c in ['r','gr','gb','b']:
  values=ns['predict']([f32(v) for v in gains[c]],grid,[2303,1727,*first,2,2])
  meshes.append(np.array([math.floor(v*1024+.5)/1024 for v in values]).reshape(13,17))
 y,x=np.indices((oh,320));tx=((x+.5)*(w/2)/320+ox)/cw;ty=((y+.5)*(h/2)/oh+oy)/ch
 gain=np.dstack([sample(meshes[0],tx,ty),sample((meshes[1]+meshes[2])/2,tx,ty),sample(meshes[3],tx,ty)])
 rgb=np.clip((base-np.array([0,128,128]))@np.linalg.inv(matrix).T/255,0,1)
 linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4);linear=np.clip(linear*gain,0,1)
 encoded=np.where(linear<=.0031308,12.92*linear,1.055*linear**(1/2.4)-.055)*255
 predicted=np.clip(encoded@matrix.T+np.array([0,128,128]),0,255)
 # Cropping changes the bar period. Derive exclusions from the baseline,
 # rather than assuming the eight bars remain forty output pixels wide.
 mask=(x>=8)&(x<312)&(y>=8)&(y<oh-8)
 edges=np.zeros((oh,320),dtype=bool);edges[:,1:]=np.max(abs(np.diff(base,axis=1)),axis=2)>4
 for shift in range(-6,7):mask &= ~np.roll(edges,shift,axis=1)
 resets=np.flatnonzero(np.median(abs(np.diff(base[:,:,0],axis=0)),axis=1)>8)+1
 for row in resets:mask[abs(y-row)<=3]=False
 error=abs(actual-predicted)[mask];change=abs(actual-base)[mask]
 rows.append(dict(mode=tag,sensor_size=[w,h],output_size=[320,oh],actual_sensor_mode_confirmed=True,grid=list(grid),sha256=sha,
  changed_components=int(np.count_nonzero(change)),mean_absolute_yuv_change=float(change.mean()),
  approximate_model_mean_error=float(error.mean()),approximate_model_p99_error=float(np.quantile(error,.99)),approximate_model_max_error=float(error.max()),compared_pixels=int(mask.sum()),edge_exclusion='baseline horizontal YUV gradient >4, expanded six pixels'))
report=dict(stage=324,sensor='imx471',run='r3',cases=rows,actual_installed_ipa_to_isp=True,factory_profile_effect_observed=True,
 internal_sensor_pattern=True,individual_values_applied=False,normal_light_optical_calibration=False,
 model_limit='Independent resampling then bilinear spatial approximation and NV12-inverted baseline; no raw optical accuracy claim',passed=True)
(HERE/'native-r3-image-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
