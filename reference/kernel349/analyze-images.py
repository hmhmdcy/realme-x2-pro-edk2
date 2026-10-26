"""Compare Gamma images only when pre-Gamma applied state is identical."""
from pathlib import Path
import json,re,struct,sys
import numpy as np
HERE=Path(__file__).resolve().parent;P=Path('E:/edk2-samurai-out/kernel349');run=sys.argv[1]
signatures=json.loads((P/'phase-signatures-private.json').read_text());root=P/('images-'+run)
observation=json.loads((P/('probe-'+run+'-observation.json')).read_text());cases=json.loads((HERE/'cases.json').read_text())
selected_runs=json.loads((P/'selected-runs-private.json').read_text()) if (P/'selected-runs-private.json').exists() else {}
def read(name,phase):
 log=observation['logs']['capture-'+name+'.log'];match=re.search(r'LSC_CONFIG stride=(\d+) frame-size=(\d+)',log);assert match
 stride,size=map(int,match.groups());image_root=P/('images-'+selected_runs.get(name,run));raw=(image_root/(name+'-phase'+str(phase)+'-private.nv12')).read_bytes();assert len(raw)==size
 width,height=map(int,cases[name]['output'].split('x'));a=np.frombuffer(raw,np.uint8)
 y=a[:stride*height].reshape(height,stride)[:,:width].astype(float)
 uv=a[stride*height:].reshape(height//2,stride//2,2)[:,:width//2].repeat(2,0).repeat(2,1).astype(float)
 return raw,np.dstack((y,uv))
def signature(name,phase):return {k:v for k,v in signatures[name][str(phase)].items() if k not in ['sof','revision']}
matrix=np.array([[.299,.587,.114],[-.168736,-.331264,.5],[.5,-.418688,-.081312]]);bias=np.array([0,128,128]);rows=[]
factory_name='s5kgw1-factory-0'
# Curves are identical across all retained sources; use the native reference
# already checked347/348, rather than embedding private table values here.
payload=(P.parent/'kernel348/factory-gamma-private.bin').read_bytes()
segments=np.frombuffer(payload[8:],dtype=np.dtype([('base','<u2'),('delta','<i2')])).reshape(3,64)
for phase in range(3):
 first,base=read('main-linear',phase);matched=signature('main-linear',phase)==signature('main-rgb',phase)
 row=dict(phase=phase,pre_gamma_state_identical=matched)
 if not matched:
  row['comparison_skipped_reason']='Different applied LSC/CCM/WB/exposure states';rows.append(row);continue
 actual_raw,actual=read('main-rgb',phase);assert first!=actual_raw
 linear=np.clip((base-bias)@np.linalg.inv(matrix).T/255,0,1)
 predicted=np.clip((linear*np.array([.5,.75,.25])*255)@matrix.T+bias,0,255)
 height,width=base.shape[:2];y,x=np.indices((height,width));mask=(x>=12)&(x<width-12)&(y>=12)&(y<height-12)
 edges=np.zeros((height,width),bool);edges[:,1:]=np.max(abs(np.diff(base,axis=1)),axis=2)>4
 for shift in range(-8,9):mask &= ~np.roll(edges,shift,axis=1)
 resets=np.flatnonzero(np.median(abs(np.diff(base[:,:,0],axis=0)),axis=1)>8)+1
 for reset in resets:mask[abs(y-reset)<=4]=False
 error=abs(actual-predicted)[mask]
 row.update(compared_pixels=int(mask.sum()),rgb_curves_change_pixels=True,asymmetric_model_mean_error=float(error.mean()),asymmetric_model_p99_error=float(np.quantile(error,.99)),asymmetric_model_max_error=float(error.max()))
 if signature('main-linear',phase)==signature(factory_name,phase):
  factory_raw,factory=read(factory_name,phase);assert factory_raw!=first
  sample=linear*64;index=np.minimum(np.floor(sample).astype(int),63);fraction=sample-index;output=np.empty_like(sample)
  for ch in range(3):output[:,:,ch]=segments['base'][ch][index[:,:,ch]]+segments['delta'][ch][index[:,:,ch]]*fraction[:,:,ch]
  model=np.clip((np.clip(output,0,1023)/1023*255)@matrix.T+bias,0,255);error=abs(factory-model)[mask]
  row.update(factory_gamma_state_identical=True,factory_curve_changes_pixels=True,factory_model_mean_error=float(error.mean()),factory_model_p99_error=float(np.quantile(error,.99)),factory_model_max_error=float(error.max()))
 rows.append(row)
assert any(r.get('rgb_curves_change_pixels') for r in rows)
assert any(r.get('factory_curve_changes_pixels') for r in rows)
assert observation['state']['summary']['passed'] and not observation['worker_live']
(HERE/('probe-'+run+'-validation.json')).write_text(json.dumps(observation['state']['summary'],indent=2)+'\n')
report=dict(stage=349,run=run,phases=rows,only_identical_pre_gamma_states_compared=True,
 actual_distinct_rgb_channel_curves_have_pixel_effect=True,factory_gamma_has_pixel_effect=True,
 no_pn9_temporal_images_compared=True,model_limit='NV12 baseline inversion with Bayer/scaling/clipping/quantization error; not RAW or optical calibration.',
 normal_light_optical_calibration=False,installed=False,passed=True)
(HERE/'gamma-image-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
