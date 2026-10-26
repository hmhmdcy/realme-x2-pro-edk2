"""Summarize original NV12 and actual metadata without exporting private pixels."""
from pathlib import Path
import json,re
import host
from nv12 import render
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;root=P/'runtime-collected-r3'
assert json.loads((HERE/'runtime-r3-validation.json').read_text())['passed']
rows=[]
for name in ['pattern-factory','scene-factory','scene-factory-isolated']:
 frames=list((root/name).glob('*.nv12'));assert len(frames)==1
 raw=frames[0].read_bytes();assert len(raw)==460800;render(raw,P/(name+'-private.png'))
 values=sorted(raw[:307200]);hist=[values.count(i) for i in range(256)]
 log=(root/(name+'.log')).read_text();meta=[dict(re.findall(r'([a-z-]+)=([^ ]+)',l)) for l in log.splitlines() if 'ADAPT_FRAME ' in l]
 assert len(meta)==24
 optical=name.startswith('scene');assert all(m['awb']==('1' if optical else '0') for m in meta)
 row=dict(capture=name,original_nv12_bytes=len(raw),frames=len(meta),test_pattern=0 if optical else 2,
  mean_y=sum(raw[:307200])/307200,p01_y=values[len(values)//100],p50_y=values[len(values)//2],p99_y=values[len(values)*99//100],
  clipped_black_fraction=sum(hist[:17])/307200,clipped_white_fraction=sum(hist[235:])/307200,
  exposure_us_min=min(int(m['exposure']) for m in meta),exposure_us_max=max(int(m['exposure']) for m in meta),
  gain_min=min(float(m['gain']) for m in meta),gain_max=max(float(m['gain']) for m in meta),
  parameter_updates=len(set((m['exposure'],m['gain'],m['red'],m['blue']) for m in meta)),saved_frame_sequence=int(frames[0].stem.split('-')[1]),
  absolute_optical_calibration_not_claimed=True)
 rows.append(row)
pattern=next((root/'pattern-factory').glob('*.nv12')).read_bytes();neutral=next((P/'runtime-collected-r2/pattern-gamma-roundtrip').glob('*.nv12')).read_bytes()
delta=[abs(a-b) for a,b in zip(pattern,neutral)]
r=dict(stage=423,rows=rows,pattern_factory_vs_neutral_mean_absolute=sum(delta)/len(delta),pattern_factory_vs_neutral_changed_bytes=sum(v!=0 for v in delta),
 pattern_factory_vs_neutral_over8=sum(v>8 for v in delta),decoded_without_app_tone_filter=True,scene_optical_test_pattern_zero=True,
 scoped_auto_capture_complete=True,full_quality_calibration_complete=False,passed=all(x['p99_y']>x['p01_y'] for x in rows) and any(v>8 for v in delta))
(HERE/'scenes-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));assert r['passed']
