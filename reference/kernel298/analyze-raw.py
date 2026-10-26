"""Measure RAW exposures and scene-only estimates; never call them dark calibration."""
from pathlib import Path
import hashlib,json,re
import numpy as np
from PIL import Image
HERE=Path(__file__).resolve().parent;P=Path('E:/edk2-samurai-out/kernel298')
capture=json.loads((HERE/'raw-capture-validation.json').read_text());assert capture['passed']
rows=[];raws=[]
for frame in [5,11,17]:
 p=P/f'raw-{frame}-private.raw';b=p.read_bytes();a=np.frombuffer(b,np.uint8).reshape(1224,2048)[:,:2040].reshape(1224,408,5).astype(np.uint16)
 raw=np.empty((1224,1632),np.uint16)
 for k in range(4):raw[:,k::4]=(a[:,:,k]<<2)|((a[:,:,4]>>(2*k))&3)
 source=re.search(r'RAW_STATS frame='+str(frame)+r' .*?mean=([\d.]+)',capture['tool_output']);assert abs(float(raw.mean())-float(source[1]))<1e-7
 channels=[raw[0::2,0::2],raw[0::2,1::2],raw[1::2,0::2],raw[1::2,1::2]]
 rows.append(dict(frame=frame,exposure_code=3000 if frame==11 else 500,analogue_gain_code=512,mean=float(raw.mean()),channels_r_gr_gb_b=[dict(mean=float(c.mean()),percentiles=np.percentile(c,[0,1,10,50,90,99,100]).tolist()) for c in channels],sha256=hashlib.sha256(b).hexdigest()))
 raws.append(raw.astype(float))
short=(raws[0]+raws[2])/2;long=raws[1]
# This fit includes scene light and cannot replace a covered-lens acquisition.
intercept=(6*short-long)/5;pedestal=float(np.median(intercept))
black=int(round(pedestal));assert 0<=black<1023
means=np.array([long[0::2,0::2].mean(),(long[0::2,1::2].mean()+long[1::2,0::2].mean())/2,long[1::2,1::2].mean()])-black
assert (means>0).all()
gains=np.clip(np.array([means[1]/means[0],1,means[1]/means[2]]),.25,4)
profile=dict(stage=298,sensor='imx319',mode=[1632,1224],bayer='RGGB10',black_dn10=black,black_u16=round(black*65535/1023),gains_rgb=gains.tolist(),gains_q10_rgb=np.rint(gains*1024).astype(int).tolist(),source='Single-scene two-exposure fit and gray-world estimate; not a dark or neutral-target calibration',factory_or_dark_calibrated=False,install_as_device_tuning=False)
(P/'scene-profile-candidate-private.json').write_text(json.dumps(profile,indent=2)+'\n')
for name,raw,gain in [('short-neutral',short,np.ones(3)),('long-neutral',long,np.ones(3)),('long-provisional',long,gains)]:
 rgb=np.stack([raw[0::2,0::2],(raw[0::2,1::2]+raw[1::2,0::2])/2,raw[1::2,1::2]],axis=2)
 linear=np.clip((rgb-black)/(1023-black)*gain,0,1);encoded=np.where(linear<=.0031308,linear*12.92,1.055*linear**(1/2.4)-.055)
 im=Image.fromarray(np.rint(encoded*255).astype(np.uint8));im.thumbnail((640,480));im.save(P/f'{name}-preview-private.png')
report=dict(stage=298,sensor='imx319',mode=[1632,1224],bayer='RGGB10',frames=rows,raw_decoder_matches_native_mean=True,
 exposure_ratio=6,scene_intercept_median_dn=pedestal,scene_intercept_percentiles=np.percentile(intercept,[1,10,50,90,99]).tolist(),
 scene_intercept_median_r_gr_gb_b=[float(np.median(intercept[y::2,x::2])) for y,x in [(0,0),(0,1),(1,0),(1,1)]],
 short_return_mean_difference=float(np.abs(raws[0]-raws[2]).mean()),dark_scene_confirmed=False,
 sensor_dark_calibration_completed=False,scene_fit_not_used_as_factory_calibration=True,
 provisional_gray_world_gains_rgb=gains.tolist(),provisional_profile_installed=False,iq_acceptance=False)
(HERE/'raw-analysis-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='frames'},indent=2))
