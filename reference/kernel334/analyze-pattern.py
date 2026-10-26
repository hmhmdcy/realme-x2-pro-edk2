"""Check CCM effects against a baseline-derived linear RGB prediction."""
from pathlib import Path
import hashlib,json,re,struct,sys
import numpy as np
HERE=Path(__file__).resolve().parent;P=Path('E:/edk2-samurai-out/kernel334');run=sys.argv[1]
data=json.loads((P/('probe-'+run+'-observation.json')).read_text());assert data['state']['terminal'] and not data['worker_live'] and data['state']['summary']['passed']
root=P/('pattern-'+run)
log=(root/'capture-pattern.log').read_text()
meta=dict((k,int(v)) for k,v in re.findall(r'(colorspace|xfer|ycbcr|quantization)=(\d+)',log))
assert meta==dict(colorspace=8,xfer=2,ycbcr=1,quantization=1),meta
def read(phase):
 raw=(root/f'pattern-private-phase{phase}.nv12').read_bytes();assert len(raw)==115200
 a=np.frombuffer(raw,np.uint8);y=a[:76800].reshape(240,320).astype(float);uv=a[76800:].reshape(120,160,2).repeat(2,0).repeat(2,1).astype(float)
 return np.dstack((y,uv)),hashlib.sha256(raw).hexdigest()
base,basehash=read(0);y,x=np.indices((240,320));mask=(x>=8)&(x<312)&(y>=8)&(y<232)
edges=np.zeros((240,320),bool);edges[:,1:]=np.max(abs(np.diff(base,axis=1)),axis=2)>4
for shift in range(-6,7):mask &= ~np.roll(edges,shift,axis=1)
resets=np.flatnonzero(np.median(abs(np.diff(base[:,:,0],axis=0)),axis=1)>8)+1
for row in resets:mask[abs(y-row)<=3]=False
yuv=np.array([[.299,.587,.114],[-.168736,-.331264,.5],[.5,-.418688,-.081312]]);bias=np.array([0,128,128])
encoded=np.clip((base-bias)@np.linalg.inv(yuv).T/255,0,1);linear=np.where(encoded<=.04045,encoded/12.92,((encoded+.055)/1.055)**2.4)
def forward(matrix,offset=None):
 v=np.clip(linear@matrix.T+(np.zeros(3) if offset is None else offset),0,1)
 gamma=np.where(v<=.0031308,12.92*v,1.055*v**(1/2.4)-.055)*255
 return np.clip(gamma@yuv.T+bias,0,255)
raw=(P/'factory-ccm-private.bin').read_bytes();fields=struct.unpack('<HHI16H',raw);assert fields[:3]==(3,2,40)
a,b,c=fields[3:6],fields[6:9],fields[9:12];q=fields[15]
signed=lambda v:(v&0x7ff)-(v&0x800)
factory=np.empty((3,3))
for hardware_row,rgb_row in enumerate([1,2,0]):factory[rgb_row]=[signed(c[hardware_row]),signed(a[hardware_row]),signed(b[hardware_row])]
factory/=1<<(7+q)
rows=[];images={}
for phase in range(8):
 actual,digest=read(phase);images[phase]=actual
 matrix=np.array([[0,0,1],[0,.75,0],[1,0,0]]) if phase==2 else factory if phase==6 else np.eye(3)
 predicted=forward(matrix);error=abs(actual-predicted)[mask]
 row=dict(phase=phase,identical_to_disabled=digest==basehash,changed_components=int(np.count_nonzero(actual-base)),
  model_mean_error=float(error.mean()),model_p99_error=float(np.quantile(error,.99)),model_max_error=float(error.max()))
 if phase==4:
  models=[]
  for scale in [1023,2047,4095,8191,16383,32767,65535]:
   err=abs(actual-forward(np.eye(3),np.array([128,-64,32])/scale))[mask]
   models.append(dict(normalization_full_scale=scale,mean_error=float(err.mean()),p99_error=float(np.quantile(err,.99))))
  row['offset_models']=models
  row['best_offset_model_full_scale']=min(models,key=lambda item:item['mean_error'])['normalization_full_scale']
 if phase==6:
  raw_rgb=(base-bias)@np.linalg.inv(yuv).T/255
  unclipped=mask & np.all((raw_rgb>.01)&(raw_rgb<.99),axis=2)
  if unclipped.any():
   inner_error=abs(actual-predicted)[unclipped]
   row['baseline_unclipped_pixels']=int(unclipped.sum())
   row['baseline_unclipped_model_mean_error']=float(inner_error.mean())
   row['baseline_unclipped_model_p99_error']=float(np.quantile(inner_error,.99))
  row['matrix_max_absolute_row_sum']=float(np.max(np.sum(abs(factory),axis=1)))
  transformed=linear@factory.T
  interior=mask & np.all((transformed>.005)&(transformed<.995),axis=2)
  if interior.any():
   interior_error=abs(actual-predicted)[interior]
   row['predicted_output_away_from_clipping_pixels']=int(interior.sum())
   row['predicted_output_away_from_clipping_model_mean_error']=float(interior_error.mean())
   row['predicted_output_away_from_clipping_model_p99_error']=float(np.quantile(interior_error,.99))
 rows.append(row)
unity_exact=all(rows[p]['identical_to_disabled'] for p in [1,3,5,7]);assert unity_exact
assert rows[2]['changed_components'] and rows[4]['changed_components']
report=dict(stage=334,run=run,colorimetry=meta,baseline_only_mask_pixels=int(mask.sum()),phases=rows,
 unity_q7_q10_and_disable_restore_exact=unity_exact,asymmetric_ccm_has_real_pixel_effect=True,signed_offsets_have_real_pixel_effect=True,
 factory_ccm_uploaded=True,factory_matrix_has_pixel_effect=bool(rows[6]['changed_components']),
 model_limit='NV12 baseline inversion; approximate Bayer/scaling/quantization/clipping. No optical accuracy claim.',
 normal_light_optical_calibration=False,ipa_cct_ccm_linked=False,installed=False,passed=True)
(HERE/('pattern-'+run+'-image-validation.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
