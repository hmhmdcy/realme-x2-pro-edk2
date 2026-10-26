from pathlib import Path
import hashlib,json,math,re,sys
import numpy as np
HERE=Path(__file__).resolve().parent;P=Path('E:/edk2-samurai-out/kernel330')
run=sys.argv[1] if len(sys.argv)>1 else 'r1'
observation=json.loads((P/('probe-'+run+'-observation.json')).read_text())
assert observation['state']['terminal'] and not observation['worker_live'] and observation['state']['summary']['passed']
cases=json.loads((P/'cases-private.json').read_text());images=P/('images-'+run)
def read(path):
 raw=path.read_bytes();assert len(raw)==115200
 a=np.frombuffer(raw,np.uint8);y=a[:76800].reshape(240,320).astype(float)
 uv=a[76800:].reshape(120,160,2).repeat(2,0).repeat(2,1).astype(float)
 return np.dstack((y,uv)),hashlib.sha256(raw).hexdigest()
old={
 's5kgw1':P.parent/'kernel325/images-r3/s5kgw1-off-4x3-private.nv12',
 'imx471':P.parent/'kernel324/capture-r3/imx471-off-4x3-private.nv12',
 's5k3m5':P.parent/'kernel323/capture-r1/off-private.nv12',
 'imx319':P.parent/'kernel322/capture-r1/off-private.nv12'}
matrix=np.array([[.299,.587,.114],[-.168736,-.331264,.5],[.5,-.418688,-.081312]])
baseline={};baseline_rows=[];rows=[]
for model,path in old.items():
 base,sha=read(images/('legacy-'+model+'-0-private.nv12'));_,oldsha=read(path)
 y,x=np.indices((240,320));mask=(x>=8)&(x<312)&(y>=8)&(y<232)
 edges=np.zeros((240,320),dtype=bool);edges[:,1:]=np.max(abs(np.diff(base,axis=1)),axis=2)>4
 for shift in range(-6,7):mask &= ~np.roll(edges,shift,axis=1)
 resets=np.flatnonzero(np.median(abs(np.diff(base[:,:,0],axis=0)),axis=1)>8)+1
 for row in resets:mask[abs(y-row)<=3]=False
 rgb=np.clip((base-np.array([0,128,128]))@np.linalg.inv(matrix).T/255,0,1)
 linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
 baseline[model]=(base,mask,linear)
 baseline_rows.append(dict(model=model,identical_to_retained_unity_reference=sha==oldsha,compared_pixels=int(mask.sum())))
for name,item in cases.items():
 base,mask,linear=baseline[item['model']]
 log=observation['logs']['capture-'+name+'.log']
 assert 'CCT_CONTROL supported=1' in log and 'white-balance-reference=1' in log
 for i,kelvin in enumerate([6500,2850]):
  actual,sha=read(images/(name+'-'+str(kelvin)+'-private.nv12'))
  r,b=[min((math.floor(v*1024+.5)+4)>>3,4095)/128 for v in item['expected_gains'][i]]
  matches=re.findall(r'CCT_FRAME sequence=(\d+) target='+str(kelvin)+r' metadata='+str(kelvin)+r' settled=1 red=([\d.e+-]+) blue=([\d.e+-]+)',log)
  assert len(matches)==1,(name,kelvin)
  assert abs(float(matches[0][1])-r)<1e-5 and abs(float(matches[0][2])-b)<1e-5
  corrected=np.clip(linear*np.array([r,1,b]),0,1)
  encoded=np.where(corrected<=.0031308,12.92*corrected,1.055*corrected**(1/2.4)-.055)*255
  predicted=np.clip(encoded@matrix.T+np.array([0,128,128]),0,255)
  error=abs(actual-predicted)[mask];difference=abs(actual-base)[mask]
  pairname=name.replace('-unit','-factory')
  pair,_=read(images/(pairname+'-'+str(kelvin)+'-private.nv12'))
  pair_delta=abs(actual-pair)[mask]
  rows.append(dict(case=name,model=item['model'],kind=item['kind'],variant=item['variant'],kelvin=kelvin,
   applied_metadata_gains_match_quantized_reference=True,settled_sequence=int(matches[0][0]),
   changed_from_unity_components=int(np.count_nonzero(difference)),
   unit_differs_from_factory=bool(np.any(pair_delta)) if item['kind']=='unit' else None,
   unit_factory_mean_difference=float(pair_delta.mean()) if item['kind']=='unit' else None,
   approximate_model_mean_error=float(error.mean()),approximate_model_p99_error=float(np.quantile(error,.99)),
   approximate_model_max_error=float(error.max())))
unit_rows=[r for r in rows if r['kind']=='unit']
report=dict(stage=330,run=run,legacy_baselines=baseline_rows,cases=rows,
 candidate_core_signed_ipa_to_isp=True,unit_white_balance_temporarily_applied=True,
 startup_6500_runtime_2850_verified=True,supplier_binding_verified=False,normal_light_optical_calibration=False,
 default_profiles_changed=False,inverse_cct_and_ccm_pending=True,
 model_limit='NV12 inverted unity baseline; Bayer/scaler and clipping approximated; no optical accuracy claim',
 passed=all(r['identical_to_retained_unity_reference'] for r in baseline_rows) and
  all(r['changed_from_unity_components'] for r in rows) and
  all(any(r['unit_differs_from_factory'] for r in unit_rows if r['variant']==variant) for variant in {r['variant'] for r in unit_rows}))
(HERE/'image-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert report['passed']
