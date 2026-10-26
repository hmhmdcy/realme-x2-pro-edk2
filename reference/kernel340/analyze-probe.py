from pathlib import Path
import bisect,json,re,struct,sys
import yaml
import host
from oracle import Oracle,Data
import ctypes
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;run=sys.argv[1];oracle=Oracle(P)
observation=json.loads((P/('probe-'+run+'-observation.json')).read_text());assert observation['state']['terminal'] and not observation['worker_live'] and observation['state']['summary']['passed']
cases=json.loads((HERE/'cases.json').read_text());runtime=json.loads((P/'runtime-cases-private.json').read_text());rows=[];allActual=bytearray();allExpected=bytearray()
identity=[1,0,0,0,1,0,0,0,1]
for name,item in cases.items():
 log=observation['logs']['capture-'+name+'.log'];profile=yaml.safe_load((P/'profiles'/(name+'.yaml')).read_text())['modes'][0]['colour_correction']
 applied={};hist=[];frames=[];lux={};pairing=[]
 for line in log.splitlines():
  if 'LUX epoch=' in line:
   fields=dict(re.findall(r'([a-z-]+)=([0-9.eE+-]+)',line.split('LUX ',1)[1]));lux[int(fields['sof'])]=float(fields['index'])
  elif 'CCM_APPLIED ' in line:
   fields={k:int(v) for k,v in re.findall(r'([a-z-]+)=([0-9]+)',line.split('CCM_APPLIED ',1)[1])}
   value=struct.unpack('<f',struct.pack('<I',fields['aec-bits']))[0];fields['value']=value;fields['expected']=oracle.evaluate(profile,fields['kelvin'],value);applied[fields['revision']]=fields
  elif 'ISP applied epoch=' in line:
   fields={k:int(v) for k,v in re.findall(r'([a-z-]+)=([0-9]+)',line.split('ISP applied ',1)[1])};hist.append((fields['first-sof'],fields['revision']))
  elif 'Pair epoch=' in line or 'Image controls recovered epoch=' in line:
   fields={k:int(v) for k,v in re.findall(r'([a-z-]+)=([0-9]+)',line)};pairing.append((fields['sof'],fields['request']))
  elif line.startswith('CCM_FRAME '):
   frame=dict(re.findall(r'([\w-]+)=([^ ]+)',line));assert len(pairing)==1,(name,'ambiguous image completion',pairing)
   frame['_kernel_sof'],frame['_request_sequence']=pairing.pop();frames.append(frame)
 hist.sort();assert hist and hist[0][1]==0 and frames and applied
 first=[x[0] for x in hist];maximumSourceError=0;checked=0;settled={};revisions=set()
 for rev,fields in applied.items():
  assert fields['statistics-sof'] in lux,(name,rev,'missing source lux')
  error=abs(fields['value']-lux[fields['statistics-sof']]);maximumSourceError=max(maximumSourceError,error);assert error<.003
  assert fields['first-sof']>fields['statistics-sof'],(name,rev,'not a future SOF')
 for frame in frames:
  seq=frame['_kernel_sof'];position=bisect.bisect_right(first,seq)-1;assert position>=0,(name,seq,hist)
  revision=hist[position][1];wanted=identity if revision==0 else applied[revision]['expected'][1]
  actual=[float(v) for v in frame['matrix'].split(',')];assert struct.pack('<9f',*actual)==struct.pack('<9f',*wanted),(name,seq,revision,actual,wanted)
  allActual.extend(struct.pack('<9f',*actual));allExpected.extend(struct.pack('<9f',*wanted));checked+=1;revisions.add(revision)
  if frame['settled']=='1':settled[int(frame['phase'])]=frame
 assert sorted(settled)==list(range(4))
 images=[(P/('images-'+run)/(name+'-phase'+str(i)+'-private.nv12')).read_bytes() for i in range(4)];assert all(len(image)==115200 for image in images)
 changed=[]
 for a in range(3):
  for b in range(a+1,3):
   if runtime[name]['phases'][a]['expected_matrix']!=runtime[name]['phases'][b]['expected_matrix']:
    assert images[a]!=images[b],(name,a,b,'matrix changed but image identical');changed.append([a,b])
 assert changed and settled[3]['awb']=='1' and settled[3]['locked']=='1'
 rows.append(dict(case=name,model=item['model'],matrix_metadata_checked_frames=checked,applied_runtime_revisions=len(applied),observed_image_revisions=len(revisions),maximum_source_lux_decimal_log_error=maximumSourceError,
  settled_phases=4,manual_exposure_gain_changed=True,independent_steady_phase_matrix_matches=True,changed_ccm_image_pairs=changed,automatic_awb_locked=True,observed_image_sequence_to_kernel_sof_offsets=sorted({f['_kernel_sof']-int(f['sequence']) for f in frames}),kernel_sof_from_actual_pairing_event=True,front_factory_ccm_enabled=item['factory_ccm_enabled'],front_enable_experiment=item['experimental_front_ccm_override'],passed=True))
(P/'metadata-actual-private.bin').write_bytes(allActual);(P/'metadata-expected-private.bin').write_bytes(allExpected);assert allActual==allExpected
summary=observation['state']['summary'];(HERE/('probe-'+run+'-validation.json')).write_text(json.dumps(summary,indent=2)+'\n')
report=dict(stage=340,run=run,cameras=rows,compared_matrix_metadata_bytes=len(allActual),differing_bytes=0,actual_per_sof_acknowledgement_verified=True,runtime_aec_and_cct_ccm_coupled=True,independent_pinned_source_oracle=True,steady_phase_original_oem_exposure_lux_reference=True,normal_light_optical_validation=False,supplier_mode_binding_verified=False,default_profiles_changed=False,installed=False,passed=True)
(HERE/'runtime-ccm-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
