"""Measure actual unit/factory effects; optical correction is not asserted."""
from pathlib import Path
import hashlib,json,struct
import numpy as np
HERE=Path(__file__).resolve().parent;P=Path('E:/edk2-samurai-out/kernel322')
def read(name):
 b=(P/'capture-r1'/(name+'-private.nv12')).read_bytes();assert len(b)==115200
 v=np.frombuffer(b,np.uint8);y=v[:76800].reshape(240,320).astype(float)
 uv=v[76800:].reshape(120,160,2).repeat(2,0).repeat(2,1).astype(float)
 return np.dstack((y,uv)),hashlib.sha256(b).hexdigest()
base,digest=read('off');matrix=np.array([[.299,.587,.114],[-.168736,-.331264,.5],[.5,-.418688,-.081312]])
rgb=np.clip((base-np.array([0,128,128]))@np.linalg.inv(matrix).T/255,0,1)
linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
y,x=np.indices((240,320));mask=(x%40>=8)&(x%40<32)&(y>=8)&(y<232)
resets=np.flatnonzero(np.median(abs(np.diff(base[:,:,0],axis=0)),axis=1)>8)+1
for row in resets:mask[abs(y-row)<=3]=False
def sample(mesh,tx,ty,cubic):
 ix=np.floor(tx).astype(int);iy=np.floor(ty).astype(int);fx=tx-ix;fy=ty-iy
 def v(dx,dy):return mesh[np.clip(iy+dy,0,12),np.clip(ix+dx,0,16)]
 if not cubic:return (v(0,0)*(1-fx)+v(1,0)*fx)*(1-fy)+(v(0,1)*(1-fx)+v(1,1)*fx)*fy
 def weights(t):return [(-t**3+2*t*t-t)/2,(3*t**3-5*t*t+2)/2,(-3*t**3+4*t*t+t)/2,(t**3-t*t)/2]
 wx,wy=weights(fx),weights(fy)
 return sum(v(c-1,r-1)*wx[c]*wy[r] for r in range(4) for c in range(4))
rows=[]
for name in ['factory','unit']:
 image,sha=read(name);raw=(P/(name+'-mesh-private.bin')).read_bytes()
 cw,ch,ox,oy,level=struct.unpack_from('<HHHHB',raw,8)
 mesh=np.array(struct.unpack_from('<884H',raw,24)).reshape(4,13,17)/1024
 tx=((x+.5)*816/320+ox)/cw;ty=((y+.5)*612/240+oy)/ch
 models=[]
 for cubic in [False,True]:
  # Mean green is the scalar approximation after Bayer reconstruction.
  gain=np.dstack([sample(mesh[0],tx,ty,cubic),sample((mesh[1]+mesh[2])/2,tx,ty,cubic),sample(mesh[3],tx,ty,cubic)])
  corrected=np.clip(linear*gain,0,1);encoded=np.where(corrected<=.0031308,12.92*corrected,1.055*corrected**(1/2.4)-.055)*255
  predicted=np.clip(encoded@matrix.T+np.array([0,128,128]),0,255)
  error=abs(image-predicted)[mask]
  models.append(dict(interpolation='cubic' if cubic else 'bilinear',mean_error=float(error.mean()),p99_error=float(np.quantile(error,.99)),maximum_error=float(error.max())))
 delta=abs(image-base)[mask]
 rows.append(dict(case=name,sha256=sha,different_from_disabled=sha!=digest,mean_absolute_yuv_change=float(delta.mean()),approximate_models=models))
factory,_=read('factory');unit,_=read('unit');delta=abs(unit-factory)[mask]
report=dict(stage=322,internal_sensor_pattern=True,actual_installed_ipa_to_isp=True,compared_pixels=int(mask.sum()),cases=rows,
 unit_differs_from_factory=bool(np.any(delta)),unit_factory_mean_absolute_yuv_difference=float(delta.mean()),
 individual_values_temporarily_applied=True,normal_light_optical_calibration=False,
 model_limit='NV12-inverted baseline, Bayer reconstruction and scaler approximated; hardware interpolation not identified by this measurement',
 passed=all(row['different_from_disabled'] for row in rows) and bool(np.any(delta)))
(HERE/'native-r1-image-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
