"""Check real observations, per-request tone programs and final numeric receipts."""
from pathlib import Path
import json,re
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;rows=[]
for attempt in ['r2','r3']:
 report=json.loads((HERE/('runtime-'+attempt+'-validation.json')).read_text());assert report['passed']
 root=P/('runtime-collected-'+attempt)
 for name,summary in report['captures'].items():
  lines=(root/(name+'.log')).read_text().splitlines();observations={};prepares={};queued=set();resolved=set();revision=0;pending=None;traces=set();histograms=set();holds=0;successful=0
  for line in lines:
   values=dict(re.findall(r'([a-z-]+)=([^ ]+)',line))
   if 'IPE_OBSERVE ' in line:observations[int(values['token'])]=values
   if 'IPE_TONE_PREPARE ' in line:
    token=int(values['token']);assert pending is None and int(values['base'])==revision and int(values['revision'])==revision+1
    assert values['histogram']==observations[token]['trace'] and values['sof']==observations[token]['sof']
    assert int(values['bytes'])==6008 and observations[token]['lux-valid']=='1' and observations[token]['gamma-override']=='1'
    prepares[token]=values;pending=token;traces.add(values['trace']);histograms.add(values['histogram'])
   if 'IPE_TONE_HOLD ' in line:holds+=1;assert int(values['revision'])==revision
   if 'IPE_TONE_QUEUE ' in line and values['fresh']=='1':
    token=int(values['token']);assert token in prepares and values['sof']==prepares[token]['sof'] and values['revision']==prepares[token]['revision'] and values['bytes']=='6008' and values['result']=='0';queued.add(token)
   if 'IPE_TONE_RECEIPT ' in line:
    token=int(values['token']);assert token==pending and token in queued and token not in resolved
    assert values['result']=='1' and values['success']=='1';revision+=1;assert int(values['revision'])==revision;pending=None;resolved.add(token);successful+=1
   if 'IPE_TONE_STOP ' in line:assert int(values['revision'])==revision and values['pending']=='0'
  if 'bypass' not in name:assert prepares and queued==resolved==set(prepares) and revision==successful
  else:assert not prepares
  assert len([l for l in lines if 'ADAPT_FRAME ' in l])==summary['frames']
  if name.endswith('isolated'):
   app=set(re.findall(r'ADAPT_PID value=(\d+)','\n'.join(lines)));ipa=set(re.findall(r'IPA stats pid=(\d+)','\n'.join(lines)));assert len(app)==1 and ipa and not app&ipa
  rows.append(dict(attempt=attempt,capture=name,image_frames=summary['frames'],prepared=len(prepares),same_sof_queued=len(queued),numeric_commits=successful,final_revision=revision,holds=holds,unique_parameter_traces=len(traces),unique_histograms=len(histograms),passed=True))
r=dict(stage=423,captures=rows,image_frames=sum(x['image_frames'] for x in rows),numeric_commits=sum(x['numeric_commits'] for x in rows),
 actual_frame_observation_to_typed_media_request_to_final_receipt=True,no_numerical_state_committed_on_queue_only=True,
 native_and_isolated_auto_scene_verified=True,private_ipa_version=3,kernel_replacement=False,formal_configuration_modified=False,
 scoped_single_exposure_path=True,android_hdr_aec_fields_not_claimed=True,full_factory_pipeline_equivalence_not_claimed=True,passed=True)
(HERE/'hardware-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
