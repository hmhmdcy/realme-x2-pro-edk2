"""Differential RGB-linear gain prediction from the uncorrected NV12 frame."""
from pathlib import Path
import hashlib,json,sys
import numpy as np
HERE=Path(__file__).resolve().parent
run=sys.argv[1] if len(sys.argv)>1 else 'r3'
root=Path('E:/edk2-samurai-out/kernel318')/('pattern-'+run)
def read(phase):
 b=(root/f'pattern-private-phase{phase}.nv12').read_bytes()
 assert len(b)==115200
 a=np.frombuffer(b,np.uint8)
 y=a[:76800].reshape(240,320).astype(float)
 uv=a[76800:].reshape(120,160,2).repeat(2,0).repeat(2,1).astype(float)
 return np.dstack((y,uv)),hashlib.sha256(b).hexdigest()
base,base_hash=read(0)
matrix=np.array([[.299,.587,.114],[-.168736,-.331264,.5],[.5,-.418688,-.081312]])
encoded=np.clip((base-np.array([0,128,128]))@np.linalg.inv(matrix).T/255,0,1)
linear=np.where(encoded<=.04045,encoded/12.92,((encoded+.055)/1.055)**2.4)
y,x=np.indices((240,320))
mask=(y>=8)&(y<232)&(x%40>=8)&(x%40<32)
# The sensor restarts its grey ramp several times vertically. Nonlinear ISP
# processing precedes MNDS scaling, so an already downscaled baseline cannot
# predict the mixed pixels at those edges. Derive the exclusions from baseline
# alone, before looking at any corrected frame.
resets=np.flatnonzero(np.median(abs(np.diff(base[:,:,0],axis=0)),axis=1)>8)+1
for row in resets:mask[abs(y-row)<=3]=False
rows=[]
phase_count=len(list(root.glob('*.nv12')))
for phase in range(phase_count):
 actual,digest=read(phase)
 gain=np.ones((240,320,3))
 if phase==2:gain*=1.5
 if phase==3:gain*=((1+(2+(x+.5)*2104/320/2)/1056)[...,None])
 if phase==4:gain*=np.array([1.5,1,1.25])
 if phase==7:gain*=((1+(18+(y+.5)*1560/240/2)/1088)[...,None])
 v=np.clip(linear*gain,0,1)
 v=np.where(v<=.0031308,12.92*v,1.055*v**(1/2.4)-.055)*255
 predicted=np.clip(v@matrix.T+np.array([0,128,128]),0,255)
 error=abs(predicted-actual)[mask]
 delta=abs(actual-base)[mask]
 rows.append(dict(phase=phase,sha256=digest,same_as_disabled=digest==base_hash,
  model_mean_absolute_error=float(error.mean()),model_p99_error=float(np.quantile(error,.99)),
  model_max_error=float(error.max()),mean_change_from_disabled=float(delta.mean())))
report=dict(stage=318,run=run,pattern='S5K3M5 fade-to-grey colour bars',
 ambient_light_required=False,model='Invert baseline YUV/sRGB, apply independent linear RGB gains, encode sRGB/YUV; exclude colour-bar boundaries and baseline-detected grey-ramp reset edges.',
 baseline_detected_reset_rows=resets.tolist(),compared_pixels=int(mask.sum()),
 phases=rows,unity_and_disable_restore_exact=all(rows[p]['same_as_disabled'] for p in ([1,5,6,8] if phase_count==9 else [1,5,6])),
 nonunity_tables_observable=all(rows[p]['mean_change_from_disabled']>1 for p in ([2,3,4,7] if phase_count==9 else [2,3,4])),
 differential_gain_prediction_passed=all(r['model_p99_error']<=3 for r in rows),
 optical_calibration_completed=False)
report['passed']=all(report[k] for k in ['unity_and_disable_restore_exact','nonunity_tables_observable','differential_gain_prediction_passed'])
(HERE/('pattern-'+run+'-image-validation.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
