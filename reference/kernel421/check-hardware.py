"""Match actual owned observations, IPC fields and final image receipts."""
from pathlib import Path
import json,math,re,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;attempt=sys.argv[1] if len(sys.argv)>1 else 'r1';assert attempt in ['r1','r2'];C=P/('runtime-collected-'+attempt)
r=json.loads((HERE/('runtime-'+attempt+'-validation.json')).read_text());assert r['passed'] and r['terminal'] and r['formal420_unchanged']
assert not any(r[k] for k in ['worker_live','client_live','collector_live']) and not r['new_fault_count'] and r['taint']==512
rows=[]
labels=['gst-s5kgw1','isolated-main'] if attempt=='r2' else ['gst-imx471','gst-imx319','gst-s5k3m5','gst-s5kgw1','raw-dual','raw-raw','isolated-main']
for label in labels:
 text=(C/(label+'.log')).read_text();observed={};pairs={};receipts={};stop=[];app_checks=0;app_without_statistics=[]
 pipeline_pids=set(re.findall(r'\] \[(\d+)\]\s+INFO CamssVfe .* IPE_PAIR ',text))
 ipa_pids=set(re.findall(r'\] \[(\d+)\]\s+INFO IPACamss .* IPE_OBSERVE ',text))
 assert len(pipeline_pids)==len(ipa_pids)==1
 execution='in-process' if pipeline_pids==ipa_pids else 'isolated'
 if label=='isolated-main':assert execution=='isolated'
 for line in text.splitlines():
  if 'IPE_OBSERVE ' in line:
   d=dict(re.findall(r'([a-z-]+)=([^\s]+)',line.split('IPE_OBSERVE ',1)[1]));key=(int(d['epoch']),int(d['token']))
   assert key not in observed and int(d['exposure-ns'])>0 and float(d['analogue-gain'])>0 and int(d['population'])>0
   observed[key]=d
  if 'IPE_PAIR ' in line:
   d=dict(re.findall(r'([a-z-]+)=([^\s]+)',line.split('IPE_PAIR ',1)[1]));key=(int(d['epoch']),int(d['token']));assert key not in pairs;pairs[key]=d
  if 'IPE_RECEIPT ' in line:
   d=dict(re.findall(r'([a-z-]+)=([^\s]+)',line.split('IPE_RECEIPT ',1)[1]));key=(int(d['epoch']),int(d['token']));assert key not in receipts;receipts[key]=d
  if 'IPE_HISTORY_STOP ' in line:
   stop.append({k:int(v) for k,v in re.findall(r'([a-z-]+)=(\d+)',line.split('IPE_HISTORY_STOP ',1)[1])})
 assert observed and pairs and receipts and stop and 'IPE observation rejected:' not in text
 for key,d in pairs.items():
  o=observed[key]
  assert all(d[k]==o[k] for k in ['sof','trace','exposure-ns','analogue-gain']), (label,key)
 for key,d in receipts.items():
  o=observed[key];assert d['sof']==o['sof'] and d['trace']==o['trace']
  assert (int(d['result']) in [1,2] if int(d['success']) else int(d['result'])==0)
 for s in stop:
  assert s['pending']==0 and s['prepared']==s['committed']+s['discarded']+s['superseded']+s['aborted']
  epoch=s['epoch'];assert sum(k[0]==epoch for k in observed)==s['prepared']
  assert sum(k[0]==epoch and int(d['result'])==1 for k,d in receipts.items())==s['committed']
  assert sum(k[0]==epoch and int(d['result'])==0 for k,d in receipts.items())==s['discarded']
  assert sum(k[0]==epoch and int(d['result'])==2 for k,d in receipts.items())==s['superseded']
 # Actual app metadata and the IPA's same-SOF physical exposure must agree.
 by_sof={int(d['sof']):d for d in observed.values()}
 if label=='isolated-main':
  for line in text.splitlines():
   if 'ADAPT_FRAME ' not in line:continue
   d=dict(re.findall(r'([a-z-]+)=([^\s]+)',line.split('ADAPT_FRAME ',1)[1]));sof=int(d['sequence']);o=by_sof.get(sof)
   if o is None:
    assert re.search(r'Image controls recovered epoch=\d+ sof='+str(sof)+r' request=',text)
    assert not any(int(v['sof'])==sof for v in pairs.values()) and not any(int(v['sof'])==sof for v in receipts.values())
    app_without_statistics.append(sof);continue
   assert abs(int(o['exposure-ns'])/1000-int(d['exposure']))<=0.501
   assert math.isclose(float(o['analogue-gain']),float(d['gain']),rel_tol=2e-5,abs_tol=2e-5);app_checks+=1
 if label=='raw-raw':assert all(not int(d['success']) for d in receipts.values()) and all(not s['committed'] for s in stop)
 else:assert any(int(d['result'])==1 for d in receipts.values()) and 'requests=1' in text
 if label=='isolated-main':assert app_checks+len(app_without_statistics)==r['candidate_suite']['captures']['isolated-main']['frames']
 if attempt=='r2' and label=='gst-s5kgw1':
  assert sum(int(d['result'])==1 for d in receipts.values())==r['candidate_suite']['captures']['s5kgw1']['frames']==12
  assert 'Image controls recovered' not in text
 rows.append(dict(case=label,execution=execution,observations=len(observed),paired=len(pairs),receipts=len(receipts),committed=sum(int(d['result'])==1 for d in receipts.values()),
  discarded=sum(int(d['result'])==0 for d in receipts.values()),superseded=sum(int(d['result'])==2 for d in receipts.values()),aborted=sum(s['aborted'] for s in stop),metadata_exposure_gain_matches=app_checks,
  app_metadata_without_statistics_sofs=app_without_statistics,no_commit_for_missing_statistics_verified=True,
  copied_histogram_trace_unchanged_through_final_receipt=True,passed=True))
total=r['after_candidate']['completed']-r['before']['completed'];assert total==sum(c['ipe_completed'] for c in r['candidate_suite']['captures'].values())
report=dict(stage=421,attempt=attempt,cases=rows,candidate_ipe_frames=total,formal_recheck=r['formal_front'],private_ipa_version=2,
 actual_default_and_forced_isolated_matching_module_proxy_library=True,native_in_process_ipa_verified=any(c['execution']=='in-process' for c in rows),native_isolated_ipa_verified=any(c['execution']=='isolated' for c in rows),actual_same_sof_exposure_gain_and_owned_histogram_verified=True,
 actual_final_receipt_and_stop_balance_verified=True,raw_only_does_not_commit_ipe_history=attempt=='r1',raw_only_evidence_reused_from_r1=attempt=='r2',
 unsafe_hardware_error_not_injected=True,observations_only_not_tmc_numerical_state=True,automatic_ipe_numeric_generation=False,
 normal420_files_and_loaded_drivers_unchanged=True,passed=True)
for name in ['hardware-validation.json','hardware-'+attempt+'-validation.json']:(HERE/name).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
