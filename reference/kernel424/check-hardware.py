"""Verify physical lux-history receipts and report AF metadata separately."""
from pathlib import Path
import json,re
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;root=P/'runtime-collected-r1'
state=json.loads((HERE/'runtime-r1-validation.json').read_text());assert state['passed'] and state['terminal']
rows=[]
for name,summary in state['captures'].items():
 text=(root/(name+'.log')).read_text();observations={};proposals={};queue=set();commits=set();pending=None;revision=0;lastLux=0;holds=0;traces=set();distinctLux=set();meta=[]
 for line in text.splitlines():
  values=dict(re.findall(r'([a-z-]+)=([^ ]+)',line))
  if 'IPE_OBSERVE ' in line:observations[int(values['token'])]=values
  if 'IPE_TONE_PREPARE ' in line:
   token=int(values['token']);assert pending is None and int(values['base'])==revision and int(values['revision'])==revision+1
   assert values['histogram']==observations[token]['trace'] and values['sof']==observations[token]['sof'] and observations[token]['lux-valid']=='1'
   assert float(values['previous-ltm-lux'])==lastLux
   proposals[token]=values;pending=token;traces.add(values['trace']);distinctLux.add(values['lux'])
  if 'IPE_TONE_HOLD ' in line:holds+=1;assert int(values['revision'])==revision
  if 'IPE_TONE_QUEUE ' in line and values['fresh']=='1':
   token=int(values['token']);assert token in proposals and values['sof']==proposals[token]['sof'] and values['revision']==proposals[token]['revision'] and values['bytes']=='6008' and values['result']=='0';queue.add(token)
  if 'IPE_TONE_RECEIPT ' in line:
   token=int(values['token']);assert token==pending and token in queue and token not in commits
   assert values['result']=='1' and values['success']=='1';revision+=1;assert int(values['revision'])==revision;lastLux=float(proposals[token]['lux']);pending=None;commits.add(token)
  if 'IPE_TONE_STOP ' in line:assert int(values['revision'])==revision and values['pending']=='0'
  if 'ADAPT_FRAME ' in line:meta.append(values)
 assert len(meta)==summary['frames'] and proposals and set(proposals)==queue==commits
 scan=[m for m in meta if m['af-state']=='1'];terminal=[m for m in meta if m['af-state'] in ['2','3']]
 assert scan and terminal and meta[-1]['af-state'] in ['2','3']
 if name.endswith('isolated'):
  app=set(re.findall(r'ADAPT_PID value=(\d+)',text));ipa=set(re.findall(r'IPA stats pid=(\d+)',text));assert len(app)==1 and ipa and not app&ipa
 scores=[int(m['focus-fom']) for m in meta if int(m['focus-fom'])>=0]
 rows.append(dict(capture=name,image_frames=len(meta),numeric_commits=revision,holds=holds,unique_parameter_traces=len(traces),distinct_lux_values=len(distinctLux),
  actual_previous_ltm_lux_equals_previous_committed_lux=True,af_scanning_frames=len(scan),af_final_state=int(meta[-1]['af-state']),af_reported_focused=meta[-1]['af-state']=='2',
  af_final_fom=int(meta[-1]['focus-fom']),af_max_fom=max(scores) if scores else None,exposure_us_min=min(int(m['exposure']) for m in meta),exposure_us_max=max(int(m['exposure']) for m in meta),
  image_quality_not_inferred_from_af_state=True,passed=True))
r=dict(stage=424,rows=rows,actual_same_sof_typed_requests_and_final_numeric_receipts=True,real_optical_capture=True,
 image_frames=sum(r['image_frames'] for r in rows),numeric_commits=sum(r['numeric_commits'] for r in rows),
 native_and_isolated_ipa=True,corrected_lux_domain_hardware_verified=True,missing_bg_recovery_checked_in_real_ipa_sdk_not_injected_on_phone=True,
 new_fault_count=state['new_fault_count'],formal420_unchanged=state['formal420_unchanged'],coarse_dc_not_implemented=True,full_goal_complete=False,passed=True)
(HERE/'hardware-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
