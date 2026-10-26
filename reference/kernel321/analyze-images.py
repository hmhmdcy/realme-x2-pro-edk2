from pathlib import Path
import hashlib,json,sys
import numpy as np
HERE=Path(__file__).resolve().parent;run=sys.argv[1] if len(sys.argv)>1 else 'r2'
P=Path('E:/edk2-samurai-out/kernel321')/('capture-'+run)
def read(name):
 b=(P/(name+'-private.nv12')).read_bytes();assert len(b)==115200
 a=np.frombuffer(b,np.uint8);y=a[:76800].reshape(240,320).astype(float)
 uv=a[76800:].reshape(120,160,2).repeat(2,0).repeat(2,1).astype(float)
 return np.dstack((y,uv)),hashlib.sha256(b).hexdigest()
base,digest=read('off');matrix=np.array([[.299,.587,.114],[-.168736,-.331264,.5],[.5,-.418688,-.081312]])
v=np.clip((base-np.array([0,128,128]))@np.linalg.inv(matrix).T/255,0,1)
linear=np.where(v<=.04045,v/12.92,((v+.055)/1.055)**2.4)
y,x=np.indices((240,320));mask=(x%40>=8)&(x%40<32)&(y>=8)&(y<232)
resets=np.flatnonzero(np.median(abs(np.diff(base[:,:,0],axis=0)),axis=1)>8)+1
for row in resets:mask[abs(y-row)<=3]=False
rows=[]
for name in ['off','unity','gain','gradient','calibrated']:
 a,sha=read(name);gain=np.ones((240,320,3))
 if name=='gain':gain*=1.5
 if name=='gradient':gain*=(1+(x+.5)*1632/320/1631+.24*(y+.5)*1224/240/1223)[...,None]
 if name=='calibrated':gain*=np.array([2.5,1.25,3.375])
 corrected=np.clip(linear*gain,0,1)
 encoded=np.where(corrected<=.0031308,12.92*corrected,1.055*corrected**(1/2.4)-.055)*255
 predicted=np.clip(encoded@matrix.T+np.array([0,128,128]),0,255)
 error=abs(a-predicted)[mask]
 rows.append(dict(case=name,sha256=sha,same_as_disabled=sha==digest,model_mean_error=float(error.mean()),model_p99_error=float(np.quantile(error,.99)),model_max_error=float(error.max())))
report=dict(stage=321,run=run,actual_ipa_to_hardware=True,internal_pattern=True,compared_pixels=int(mask.sum()),excluded_baseline_reset_rows=resets.tolist(),
 cases=rows,unity_exact=rows[1]['same_as_disabled'],model_passed=all(r['model_p99_error']<=3 for r in rows),individual_values_applied=False,normal_light_optical_calibration=False)
report['passed']=report['unity_exact'] and report['model_passed']
(HERE/('native-'+run+'-image-validation.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
