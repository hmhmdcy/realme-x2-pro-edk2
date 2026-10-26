from pathlib import Path
import importlib.util,json,math,re,struct,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;run=sys.argv[1]
spec=importlib.util.spec_from_file_location('stock_inverse',HERE.parent/'kernel331/stock_inverse.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
engine=mod.StockInverse(P.parent/'kernel328/stats-source/com.qti.stats.awb.so')
data=json.loads((P/('probe-'+run+'-observation.json')).read_text())
assert data['state']['terminal'] and not data['worker_live'] and data['state']['summary']['passed']
cases=json.loads((P/'cases-private.json').read_text());rows=[]
f32=lambda v:struct.unpack('<f',struct.pack('<f',v))[0]
for name,case in cases.items():
 if case['kind']!='unit':continue
 values=struct.unpack('<20f',(P/(name+'-points-private.bin')).read_bytes());points=[list(values[i:i+2]) for i in range(0,20,2)]
 engine.configure(points);log=data['logs']['capture-'+name+'.log']
 frames=[]
 for line in log.splitlines():
  if not line.startswith('CCT_FRAME '):continue
  fields=dict(re.findall(r'(\w+)=([-+.\deE]+)',line))
  if 'red' not in fields or 'blue' not in fields or not int(fields['metadata']):continue
  red,blue=float(fields['red']),float(fields['blue']);assert red>0 and blue>0
  cct=engine.estimate([f32(1/red),f32(1/blue)])[1]
  expected=math.floor(cct+.5);error=abs(int(fields['metadata'])-expected)
  assert error<=1,(name,line,expected)
  frames.append(dict(fields=fields,error=error))
 manual=[f for f in frames if f['fields']['awb']=='0'];auto=[f for f in frames if f['fields']['awb']=='1']
 assert manual and auto
 assert any(f['fields']['settled']=='1' for f in manual)
 assert any(f['fields']['settled']=='1' and f['fields']['locked']=='1' for f in auto)
 images=list((P/('images-'+run)).glob(name+'-*-private.nv12'));assert len(images)==2 and all(p.stat().st_size==115200 for p in images)
 rows.append(dict(case=name,model=case['model'],metadata_checked_frames=len(frames),manual_frames=len(manual),automatic_frames=len(auto),
  maximum_cct_rounding_error_kelvin=max(f['error'] for f in frames),automatic_awb_locked=True,stable_images=len(images),
  automatic_image_differs_from_manual=images[0].read_bytes()!=images[1].read_bytes()))
report=dict(stage=332,run=run,cases=rows,estimated_cct_matches_independent_stock_oracle=True,
 manual_to_automatic_awb_transition_verified=True,unit_reference_points_applied=True,normal_light_optical_calibration=False,
 ccm_pending=True,default_profiles_changed=False,installed=False,passed=len(rows)==5)
(HERE/'cct-metadata-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
