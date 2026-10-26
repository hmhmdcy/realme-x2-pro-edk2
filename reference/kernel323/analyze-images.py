from pathlib import Path
import hashlib,json
import numpy as np
HERE=Path(__file__).resolve().parent;P=Path('E:/edk2-samurai-out/kernel323/capture-r1')
rows=[];images=[]
for name in ['off','factory']:
 raw=(P/(name+'-private.nv12')).read_bytes();assert len(raw)==115200
 image=np.frombuffer(raw,np.uint8).astype(float);images.append(image)
 rows.append(dict(case=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),y_mean=float(image[:76800].mean()),y_min=float(image[:76800].min()),y_max=float(image[:76800].max())))
change=abs(images[1]-images[0]);changed=int(np.count_nonzero(change));assert changed
report=dict(stage=323,sensor='s5k3m5',actual_installed_ipa_to_isp=True,internal_sensor_pattern=True,cases=rows,
 changed_components=changed,total_components=len(change),mean_absolute_yuv_change=float(change.mean()),
 factory_profile_effect_observed=True,individual_values_applied=False,normal_light_optical_calibration=False,passed=True)
(HERE/'native-r1-image-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
