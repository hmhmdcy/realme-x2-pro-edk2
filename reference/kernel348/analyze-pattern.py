"""Check real Gamma effects, enable semantics and coexistence with LSC."""
from pathlib import Path
import json,re,struct,sys
import numpy as np
HERE=Path(__file__).resolve().parent;P=Path('E:/edk2-samurai-out/kernel348');run=sys.argv[1]
observation=json.loads((P/('probe-'+run+'-observation.json')).read_text())
assert observation['state']['terminal'] and not observation['worker_live'] and observation['state']['summary']['passed']
root=P/('pattern-'+run);log=(root/'capture-pattern.log').read_text()
meta={k:int(v) for k,v in re.findall(r'(colorspace|xfer|ycbcr|quantization)=(\d+)',log)}
format_match=re.search(r'FORMAT video=\S+ width=(\d+) height=(\d+) stride=(\d+) sizeimage=(\d+)',log);assert format_match
width,height,stride,size=map(int,format_match.groups());assert (width,height)==(320,240)
raw={phase:(root/f'pattern-private-phase{phase}.nv12').read_bytes() for phase in range(10)}
def decode(data):
 assert len(data)==size
 a=np.frombuffer(data,np.uint8);y=a[:stride*height].reshape(height,stride)[:,:width].astype(float)
 uv=a[stride*height:].reshape(height//2,stride//2,2)[:,:width//2].repeat(2,0).repeat(2,1).astype(float)
 return np.dstack((y,uv))
images={p:decode(data) for p,data in raw.items()}
equal=lambda a,b:raw[a]==raw[b]
checks=dict(factory_restore_exact=equal(3,6),unity_lsc_with_gamma_exact=equal(3,7),
 upload_while_disabled_has_no_pixel_effect=equal(4,5),rec709_restore_exact=equal(0,9),
 factory_curve_changes_pixels=not equal(0,3),asymmetric_red_curve_changes_pixels=not equal(1,2),
 nonunity_lsc_with_gamma_changes_pixels=not equal(7,8),linear_and_bypass_equal=equal(1,4))
assert all(checks.values()),checks
# The capture's actual format identifies full-range BT.601 conversion. Gamma
# is deliberately changed by the test, so no inverse advertised xfer is used.
assert meta['ycbcr']==1 and meta['quantization']==1,meta
matrix=np.array([[.299,.587,.114],[-.168736,-.331264,.5],[.5,-.418688,-.081312]])
bias=np.array([0,128,128]);base=images[1]
linear=np.clip((base-bias)@np.linalg.inv(matrix).T/255,0,1)
y,x=np.indices((height,width));mask=(x>=8)&(x<width-8)&(y>=8)&(y<height-8)
edges=np.zeros((height,width),bool);edges[:,1:]=np.max(abs(np.diff(base,axis=1)),axis=2)>4
for shift in range(-6,7):mask &= ~np.roll(edges,shift,axis=1)
resets=np.flatnonzero(np.median(abs(np.diff(base[:,:,0],axis=0)),axis=1)>8)+1
for row in resets:mask[abs(y-row)<=3]=False
fields=np.frombuffer((P/'factory-gamma-private.bin').read_bytes()[8:],dtype=np.dtype([('base','<u2'),('delta','<i2')])).reshape(3,64)
def transform(value):
 sample=np.clip(value,0,1)*64;index=np.minimum(np.floor(sample).astype(int),63);fraction=sample-index
 result=np.empty_like(sample)
 for ch in range(3):result[:,:,ch]=fields['base'][ch][index[:,:,ch]]+fields['delta'][ch][index[:,:,ch]]*fraction[:,:,ch]
 return np.clip(result,0,1023)/1023
rows=[]
for phase in [2,3,7,8]:
 value=linear.copy()
 if phase==2:value[:,:,0]*=.5;output=value
 else:
  if phase==8:value*=1.5
  output=transform(value)
 predicted=np.clip((output*255)@matrix.T+bias,0,255);error=abs(images[phase]-predicted)[mask]
 rows.append(dict(phase=phase,model_mean_error=float(error.mean()),model_p99_error=float(np.quantile(error,.99)),model_max_error=float(error.max())))
# Validate parameter ACK/image pairing from actual recorded sequence numbers.
events=[dict(phase=int(p),image_sof=int(i),parameter_first_sof=int(a)) for p,i,a in re.findall(r'GAMMA_FRAME phase=(\d+) sequence=(\d+) parameter_sequence=(\d+) settled=1',log)]
assert [e['phase'] for e in events]==list(range(10)) and all(e['image_sof']>=e['parameter_first_sof'] for e in events)
assert log.count('PARAM_REJECT ')==4
report=dict(stage=348,run=run,phases=10,observed_frames=observation['state']['summary']['captures']['pattern']['frames'],
 checks=checks,colorimetry=meta,parameter_ack_and_saved_image_sofs=events,invalid_packets_rejected=4,
 baseline_only_mask_pixels=int(mask.sum()),approximate_pixel_model=rows,
 model_limit='NV12 linear baseline inversion; Bayer/scaling/clipping/quantization remain approximate.',
 normal_light_optical_calibration=False,factory_gamma_ipa_integrated=False,installed=False,passed=True)
(HERE/('pattern-'+run+'-image-validation.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
