"""Check the installed IPA's applied parameters against the existing oracle."""
from pathlib import Path
import bisect,importlib.util,json,re,struct,sys,yaml
import host

HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('oracle341',HERE.parent/'kernel341/oracle.py')
oracle341=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle341)
oracle=oracle341.LscOracle(P.parent/'kernel341')
run=sys.argv[1];d=json.loads((P/('probe-'+run+'-observation.json')).read_text())
assert d['state']['terminal'] and not d['worker_live']
summary=d['state']['summary'];cases=json.loads((HERE/'cases.json').read_text())
assert summary['deployment_restored'] and not summary['taint'] and not any(summary['fault_delta'].values())
rows=[];ccm_bytes=0
for name,item in cases.items():
 capture=summary['captures'][name];log=d['logs']['capture-'+name+'.log']
 profile=yaml.safe_load((P/'profiles'/(name+'.yaml')).read_text());size=list(map(int,item['sensor_size'].split('x')))
 mode=next(m for m in profile['modes'] if [m['match']['width'],m['match']['height']]==size)
 lsc=mode['lens_shading'];colour=mode['colour_correction'];states={};ccms={};hist=[];contexts={};frames=[];pairing=[];lux={}
 for line in log.splitlines():
  if 'LUX epoch=' in line:
   values=dict(re.findall(r'([a-z-]+)=([0-9.eE+-]+)',line.split('LUX ',1)[1]));lux[int(values['sof'])]=float(values['index'])
  elif 'LSC_APPLIED ' in line:
   fields={k:int(v) for k,v in re.findall(r'([a-z-]+)=([0-9]+)',line.split('LSC_APPLIED ',1)[1])}
   value=struct.unpack('<f',struct.pack('<I',fields['aec-bits']))[0]
   expected=oracle.evaluate(lsc,fields['kelvin'],value,size) if fields['kelvin'] else oracle.unity(lsc,size)
   assert oracle341.trace(expected)==fields['mesh-trace'],(name,'LSC trace mismatch')
   fields['value']=value;states[fields['revision']]=fields
  elif 'CCM_APPLIED ' in line:
   fields={k:int(v) for k,v in re.findall(r'([a-z-]+)=([0-9]+)',line.split('CCM_APPLIED ',1)[1])}
   value=struct.unpack('<f',struct.pack('<I',fields['aec-bits']))[0];ccms[fields['revision']]=oracle.ccm.evaluate(colour,fields['kelvin'],value)[1]
  elif 'ISP applied epoch=' in line:
   fields={k:int(v) for k,v in re.findall(r'([a-z-]+)=([0-9]+)',line.split('ISP applied ',1)[1])};hist.append((fields['first-sof'],fields['revision']))
  elif 'LSC_CONTEXT ' in line:
   fields={k:int(v) for k,v in re.findall(r'([a-z-]+)=([0-9]+)',line.split('LSC_CONTEXT ',1)[1])};contexts[fields['sof']]=fields
  elif 'Pair epoch=' in line or 'Image controls recovered epoch=' in line:
   fields={k:int(v) for k,v in re.findall(r'([a-z-]+)=([0-9]+)',line)};pairing.append((fields['sof'],fields['request']))
  elif line.startswith('CCM_FRAME '):
   fields=dict(re.findall(r'([\w-]+)=([^ ]+)',line));assert len(pairing)==1,(name,pairing)
   fields['_sof'],fields['_request']=pairing.pop();frames.append(fields)
 hist.sort();first=[entry[0] for entry in hist];seen=set();settled={};source_error=0
 for state in states.values():
  if not state['kelvin']:continue
  assert state['statistics-sof'] in lux and state['first-sof']>state['statistics-sof']
  source_error=max(source_error,abs(state['value']-lux[state['statistics-sof']]))
 assert source_error<.003
 for frame in frames:
  sof=frame['_sof'];position=bisect.bisect_right(first,sof)-1;assert position>=0
  revision=hist[position][1];state=states[revision];seen.add(state['mesh-trace'])
  if sof in contexts:assert contexts[sof]['revision']==revision and contexts[sof]['mesh-trace']==state['mesh-trace']
  if colour['enabled']:
   wanted=[1,0,0,0,1,0,0,0,1] if revision==0 else ccms[revision]
   actual=list(map(float,frame['matrix'].split(',')))
   assert struct.pack('<9f',*actual)==struct.pack('<9f',*wanted),(name,sof,'CCM mismatch');ccm_bytes+=36
  else:assert 'matrix' not in frame
  if frame['settled']=='1':settled[int(frame['phase'])]=frame
 passed=capture['probe_passed'] and sorted(settled)==[0,1,2,3] and settled[3]['locked']=='1' and len(seen)>1
 rows.append(dict(model=item['model'],profile=name,frames=len(frames),applied_lsc_states=len(states),distinct_applied_meshes=len(seen),
  actual_kernel_sof_checked=True,independent_lsc_trace_matches=True,source_lux_decimal_max_error=source_error,
  automatic_awb_locked=settled.get(3,{}).get('locked')=='1',front_factory_ccm_disable_preserved=item['model']=='imx471' and not colour['enabled'],passed=passed))
report=dict(stage=342,run=run,installed_core_and_ipa=True,cases=rows,ccm_matrix_metadata_compared_bytes=ccm_bytes,
 installed_package_compatibility=summary,normal_light_optical_calibration=False,mode_specific_exposure_table_binding_verified=False,
 default_profiles_changed=False,passed=summary['passed'] and len(rows)==4 and all(row['passed'] for row in rows))
(HERE/'installed-iq-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert report['passed']
