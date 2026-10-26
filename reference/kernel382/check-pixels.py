"""Inspect private real IPE output against the known synthetic input."""
from pathlib import Path
from collections import Counter
import hashlib,json,math,zlib
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
runtime=json.loads((HERE/'boot-runtime-validation.json').read_text());assert runtime['passed']
d=runtime['device_result'];output=(P/'collected-r1/ipe-output-private.nv12').read_bytes();assert len(output)==460800
source=bytearray(460800)
for y in range(480):
 for x in range(640):source[y*640+x]=16+((x//8+y//8*3)%28)*8
for y in range(240):
 for x in range(0,640,2):source[307200+y*640+x]=96+(x//80%2)*64;source[307200+y*640+x+1]=64+(y//60%2)*96
crc=lambda data:(zlib.crc32(data,0xffffffff)^0xffffffff)&0xffffffff
assert crc(source)==d['input_crc'] and crc(output)==d['output_crc']
(P/'ipe-input-private.nv12').write_bytes(source)
def metrics(a,b):
 n=len(a);assert len(b)==n
 sa=sum(a);sb=sum(b);aa=sum(v*v for v in a);bb=sum(v*v for v in b);ab=sum(x*y for x,y in zip(a,b))
 variance=(n*aa-sa*sa)*(n*bb-sb*sb)
 return dict(bytes=n,exact_bytes=sum(x==y for x,y in zip(a,b)),mae=sum(abs(x-y) for x,y in zip(a,b))/n,
  rmse=math.sqrt(sum((x-y)**2 for x,y in zip(a,b))/n),correlation=(n*ab-sa*sb)/math.sqrt(variance) if variance else None,
  input_mean=sa/n,output_mean=sb/n,output_min=min(b),output_max=max(b),output_unique_values=len(set(b)),sentinel_bytes=b.count(0xa5))
planes={name:metrics(source[a:b],output[a:b]) for name,a,b in [('Y',0,307200),('UV',307200,460800),('U',307200,460800)] if name!='U'}
planes['U']=metrics(source[307200::2],output[307200::2]);planes['V']=metrics(source[307201::2],output[307201::2])
quarter=bytes(v//4 for v in source)
shifted={name:metrics(quarter[a:b],output[a:b]) for name,a,b in [('Y',0,307200),('UV',307200,460800)]}
identity=source==output
levels=planes['Y']['exact_bytes']==307200 and planes['UV']['mae']<1.0
transfer=levels and not any(p['sentinel_bytes'] for p in planes.values())
report=dict(stage=382,actual_phone_output=True,synthetic_input=True,image_bytes=len(output),input_crc32_le=d['input_crc'],output_crc32_le=d['output_crc'],
 input_sha256=hashlib.sha256(source).hexdigest(),output_sha256=hashlib.sha256(output).hexdigest(),kernel_crc_values_match=True,
 planes=planes,quarter_scale_comparison=shifted,exact_identity=identity,actual_pixel_transfer_verified=transfer,
 nv12_identity_or_expected_level_validation_passed=levels,prior_zero_iq_output_level_mismatch_corrected=levels,
 four_ica_defaults_changed_together_not_single_field_hardware_isolation=True,full_iq_or_optical_calibration_proven=False,
 passed=transfer)
(HERE/'pixels-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
