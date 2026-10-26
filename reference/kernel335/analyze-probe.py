from pathlib import Path
import importlib.util,json,math,re,struct,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;run=sys.argv[1]
spec=importlib.util.spec_from_file_location('stock_inverse',HERE.parent/'kernel331/stock_inverse.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
engine=mod.StockInverse(P.parent/'kernel328/stats-source/com.qti.stats.awb.so')
data=json.loads((P/('probe-'+run+'-observation.json')).read_text());assert data['state']['terminal'] and not data['worker_live'] and data['state']['summary']['passed']
cases=json.loads((P/'cases-private.json').read_text());runtime=json.loads((HERE/'cases.json').read_text());manual=struct.unpack('<9f',(P/'manual-oracle-private.bin').read_bytes()[40:]);rows=[]
f32=lambda v:struct.unpack('<f',struct.pack('<f',v))[0]
for name in runtime:
 case=cases[name];values=struct.unpack('<20f',(P/(name+'-points-private.bin')).read_bytes());engine.configure([list(values[i:i+2]) for i in range(0,20,2)])
 oracle=(P/'profiles'/(name+'-oracle-private.bin')).read_bytes();log=data['logs']['capture-'+name+'.log'];checked=0;estimated=[];settled=[]
 for line in log.splitlines():
  if not line.startswith('CCM_FRAME '):continue
  fields=dict(re.findall(r'([\w-]+)=([^ ]+)',line));kelvin=int(fields['metadata']);phase=int(fields['phase'])
  if not kelvin:continue
  assert 1500<=kelvin<=12000 and 'matrix' in fields
  actual=tuple(float(v) for v in fields['matrix'].split(','));wanted=struct.unpack_from('<9f',oracle,(kelvin-1500)*76+40)
  assert actual==wanted or phase in [2,3] and actual==manual,(name,line,wanted)
  checked+=1
  if phase in [4,5] and (phase==5 and fields['awb']=='1' or fields['red']=='1.25' and fields['blue']=='0.75'):
   red,blue=float(fields['red']),float(fields['blue']);expected=math.floor(engine.estimate([f32(1/red),f32(1/blue)])[1]+.5)
   error=abs(kelvin-expected);assert error<=1,(name,line,expected);estimated.append(error)
  if fields['settled']=='1':settled.append(phase)
 assert settled==list(range(6)) and estimated
 images=[(P/('images-'+run)/(name+'-phase'+str(i)+'-private.nv12')).read_bytes() for i in range(6)]
 assert all(len(image)==115200 for image in images)
 assert images[0]==images[3],name+' explicit6500 restore differs'
 assert images[1]!=images[0] and images[2]!=images[1] and images[4]!=images[5],name+' expected image change absent'
 rows.append(dict(case=name,model=case['model'],matrix_metadata_checked_frames=checked,estimated_cct_checked_frames=len(estimated),maximum_estimated_cct_error_kelvin=max(estimated),
  settled_phases=6,manual_matrix_image_changed=True,restored_cct6500_image_identical=True,automatic_awb_locked=True,front_factory_enable_override=case.get('experimental_enable_override',False)))
report=dict(stage=335,run=run,cases=rows,ccm_cct_manual_gains_and_awb_coupled=True,independent_pinned_source_matrix_expectations=True,independent_stock_instruction_inverse_cct=True,
 normal_light_optical_calibration=False,non_cct_trigger_coordinates_are_reference_values=True,supplier_binding_verified=False,default_profiles_changed=False,installed=False,passed=len(rows)==5)
(HERE/('probe-'+run+'-validation.json')).write_text(json.dumps(data['state']['summary'],indent=2)+'\n')
(HERE/'ccm-metadata-image-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
