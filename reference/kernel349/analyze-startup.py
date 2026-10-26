"""Compare equal-SOF startup samples without crossing a matrix transition."""
from pathlib import Path
import bisect,json,re
import numpy as np
HERE=Path(__file__).resolve().parent;P=Path('E:/edk2-samurai-out/kernel349');root=P/'images-r2'
observation=json.loads((P/'probe-r2-observation.json').read_text());assert observation['state']['summary']['passed'] and not observation['worker_live']
matrix=np.array([[.299,.587,.114],[-.168736,-.331264,.5],[.5,-.418688,-.081312]]);bias=np.array([0,128,128])
def read(name,sequence):
 a=np.frombuffer((root/(name+'-startup'+str(sequence)+'-private.nv12')).read_bytes(),np.uint8);assert a.size==460800
 return np.dstack((a[:307200].reshape(480,640),a[307200:].reshape(240,320,2).repeat(2,0).repeat(2,1))).astype(float)
def state(name,sequence):
 log=observation['logs']['capture-'+name+'.log'];fields=[];history=[];lsc={}
 for line in log.splitlines():
  if line.startswith('GAMMA_FRAME phase=0 '):fields.append(dict(re.findall(r'([\w-]+)=([^ ]+)',line)))
  elif 'ISP applied epoch=' in line:
   row={k:int(v) for k,v in re.findall(r'([a-z-]+)=([0-9]+)',line.split('ISP applied ',1)[1])};history.append((row['first-sof'],row['revision']))
  elif 'LSC_APPLIED ' in line:
   row={k:int(v) for k,v in re.findall(r'([a-z-]+)=([0-9]+)',line.split('LSC_APPLIED ',1)[1])};lsc[row['revision']]=row['mesh-trace']
 row=next(r for r in fields if int(r['sequence'])==sequence)
 history.sort();revision=history[bisect.bisect_right([h[0] for h in history],sequence)-1][1]
 return {k:row[k] for k in ['matrix','red','blue','exposure','gain']}|dict(trace=lsc[revision])
rows=[]
for sequence in range(4):
 same=state('main-linear',sequence)==state('main-rgb',sequence);assert same
 base=read('main-linear',sequence);actual=read('main-rgb',sequence)
 linear=np.clip((base-bias)@np.linalg.inv(matrix).T/255,0,1)
 prediction=np.clip((linear*np.array([.5,.75,.25])*255)@matrix.T+bias,0,255)
 y,x=np.indices((480,640));mask=(x>=12)&(x<628)&(y>=12)&(y<468)
 edges=np.zeros((480,640),bool);edges[:,1:]=np.max(abs(np.diff(base,axis=1)),axis=2)>4
 for shift in range(-8,9):mask &= ~np.roll(edges,shift,axis=1)
 resets=np.flatnonzero(np.median(abs(np.diff(base[:,:,0],axis=0)),axis=1)>8)+1
 for reset in resets:mask[abs(y-reset)<=4]=False
 error=abs(actual-prediction)[mask]
 rows.append(dict(sequence=sequence,applied_state_identical=same,compared_pixels=int(mask.sum()),mean_error=float(error.mean()),p99_error=float(np.quantile(error,.99))))
passed=all(r['p99_error']<=3 for r in rows)
report=dict(stage=349,run='r2',same_sequence_rgb_models=rows,baseline_only_edge_exclusion=True,
 startup_gamma_channel_response_consistent=passed,capture_stability_now_includes_matrix_state=True,
 original_r1_snapshot_comparison_not_accepted=True,all_hardware_parameters_physical_latch_timing_not_inferred_from_this_model=True,
 normal_light_optical_calibration=False,passed=passed)
(HERE/'startup-boundary-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert passed
