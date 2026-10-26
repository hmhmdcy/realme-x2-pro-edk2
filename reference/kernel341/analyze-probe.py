from pathlib import Path
import bisect,json,re,struct,sys,yaml
import host
from oracle import LscOracle,trace
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;runs=sys.argv[1].split(',');oracle=LscOracle(P)
observations={};manifests={};selected={};safety=[]
for run in runs:
 d=json.loads((P/('probe-'+run+'-observation.json')).read_text());assert d['state']['terminal'] and not d['worker_live']
 summary=d['state']['summary'];assert summary['deployment_restored'] and not summary['taint'] and not any(summary['fault_delta'].values())
 observations[run]=d;manifest=HERE/('cases-'+run+'.json');manifests[run]=json.loads((manifest if manifest.exists() else HERE/'cases.json').read_text())
 safety.append(dict(run=run,passed=summary['passed'],capture_failures=d['state'].get('capture_failures',{}),deployment_restored=True))
 (HERE/('probe-'+run+'-validation.json')).write_text(json.dumps(summary,indent=2)+'\n')
 for name,capture in summary['captures'].items():
  if not capture['frames'] or not capture['settled_phases']:continue
  rank=(capture['settled_phases'],capture['probe_passed'],runs.index(run))
  if name not in selected or rank>selected[name][0]:selected[name]=(rank,run,manifests[run][name],capture)
rows=[];pairs={};ccmBytes=0
cases={name:value[2] for name,value in selected.items()}
for name,item in cases.items():
 _,run,_,capture=selected[name];d=observations[run]
 log=d['logs']['capture-'+name+'.log'];profile=yaml.safe_load((P/'profiles'/(name+'.yaml')).read_text());size=list(map(int,item['sensor_size'].split('x')));mode=next(m for m in profile['modes'] if [m['match']['width'],m['match']['height']]==size);lsc=mode['lens_shading'];colour=mode['colour_correction']
 states={};ccms={};hist=[];contexts={};frames=[];pairing=[];lux={}
 for line in log.splitlines():
  if 'LUX epoch=' in line:
   values=dict(re.findall(r'([a-z-]+)=([0-9.eE+-]+)',line.split('LUX ',1)[1]));lux[int(values['sof'])]=float(values['index'])
  elif 'LSC_APPLIED ' in line:
   fields={k:int(v) for k,v in re.findall(r'([a-z-]+)=([0-9]+)',line.split('LSC_APPLIED ',1)[1])};value=struct.unpack('<f',struct.pack('<I',fields['aec-bits']))[0]
   expected=oracle.evaluate(lsc,fields['kelvin'],value,size) if fields['kelvin'] else oracle.unity(lsc,size)
   assert trace(expected)==fields['mesh-trace'],(name,fields,'LSC trace mismatch');fields['expected']=expected;fields['value']=value;states[fields['revision']]=fields
  elif 'CCM_APPLIED ' in line:
   fields={k:int(v) for k,v in re.findall(r'([a-z-]+)=([0-9]+)',line.split('CCM_APPLIED ',1)[1])};value=struct.unpack('<f',struct.pack('<I',fields['aec-bits']))[0];ccms[fields['revision']]=oracle.ccm.evaluate(colour,fields['kelvin'],value)[1]
  elif 'ISP applied epoch=' in line:
   fields={k:int(v) for k,v in re.findall(r'([a-z-]+)=([0-9]+)',line.split('ISP applied ',1)[1])};hist.append((fields['first-sof'],fields['revision']))
  elif 'LSC_CONTEXT ' in line:
   fields={k:int(v) for k,v in re.findall(r'([a-z-]+)=([0-9]+)',line.split('LSC_CONTEXT ',1)[1])};contexts[fields['sof']]=fields
  elif 'Pair epoch=' in line or 'Image controls recovered epoch=' in line:
   fields={k:int(v) for k,v in re.findall(r'([a-z-]+)=([0-9]+)',line)};pairing.append((fields['sof'],fields['request']))
  elif line.startswith('CCM_FRAME '):
   fields=dict(re.findall(r'([\w-]+)=([^ ]+)',line));assert len(pairing)==1,(name,pairing);fields['_sof'],fields['_request']=pairing.pop();frames.append(fields)
 hist.sort();first=[row[0] for row in hist];settled={};checked=0;sourceError=0;seen=set()
 for revision,state in states.items():
  if not state['kelvin']:continue
  assert state['statistics-sof'] in lux and state['first-sof']>state['statistics-sof']
  sourceError=max(sourceError,abs(state['value']-lux[state['statistics-sof']]))
 assert sourceError<.003
 for frame in frames:
  sof=frame['_sof'];revision=hist[bisect.bisect_right(first,sof)-1][1];state=states[revision];seen.add(state['mesh-trace'])
  if sof in contexts:assert contexts[sof]['revision']==revision and contexts[sof]['mesh-trace']==state['mesh-trace']
  if colour['enabled']:
   wanted=[1,0,0,0,1,0,0,0,1] if revision==0 else ccms[revision];actual=list(map(float,frame['matrix'].split(',')));assert struct.pack('<9f',*actual)==struct.pack('<9f',*wanted),(name,sof,'ccm');ccmBytes+=36
  else:assert 'matrix' not in frame
  checked+=1
  if frame['settled']=='1':settled[int(frame['phase'])]=(frame,state)
 completed=capture['settled_phases'];assert completed>=3 and sorted(settled)==list(range(completed)) and len(seen)>1
 images=[(P/('images-'+run)/(name+'-phase'+str(i)+'-private.nv12')).read_bytes() for i in range(completed)];assert all(len(image)==115200 for image in images)
 awb=completed==4 and settled[3][0]['awb']=='1' and settled[3][0]['locked']=='1'
 if item['test_pattern']!=4:pairs[item['model'],item['kind']]=images
 rows.append(dict(case=name,run=run,model=item['model'],kind=item['kind'],test_pattern=item['test_pattern'],image_frames_checked=checked,applied_lsc_states=len(states),distinct_applied_meshes=len(seen),independent_mesh_trace_matches=True,source_lux_decimal_max_error=sourceError,settled_phases=completed,automatic_awb_locked=awb,front_factory_ccm_disable_preserved=item['model']=='imx471' and not colour['enabled'],numerical_checks_passed=True))
comparison=[]
for model in ['s5kgw1','imx471','imx319','s5k3m5']:
 for kind in ['factory','unit']:
  if (model,kind) not in pairs:
   for run in runs:
    for name,item in manifests[run].items():
     capture=observations[run]['state']['summary']['captures'].get(name,{})
     if item['model']==model and item['kind']==kind and item['test_pattern']!=4 and capture.get('settled_phases',0)>=3:
      paths=[P/('images-'+run)/(name+'-phase'+str(i)+'-private.nv12') for i in range(3)]
      if all(p.is_file() for p in paths):pairs[model,kind]=[p.read_bytes() for p in paths]
 changed=[phase for phase,(a,b) in enumerate(zip(pairs[model,'factory'],pairs[model,'unit'])) if a!=b];assert changed,(model,'unit LSC had no visible effect')
 comparison.append(dict(model=model,changed_factory_unit_phases=changed,passed=True))
report=dict(stage=341,runs=safety,cases=rows,factory_unit_image_comparisons=comparison,ccm_matrix_metadata_compared_bytes=ccmBytes,dynamic_lsc_trace_checked_against_original_functions_and_independent_resampler=True,trace_is_diagnostic_not_factory_checksum=True,actual_kernel_sof_pairing=True,numerical_checks_passed=len(rows)==8,all_four_camera_factory_unit_awb_locked=all(row['automatic_awb_locked'] for row in rows),normal_light_optical_calibration=False,supplier_mode_binding_verified=False,default_profiles_changed=False,installed=False,passed=len(rows)==8 and all(row['automatic_awb_locked'] for row in rows))
(HERE/'runtime-lsc-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
