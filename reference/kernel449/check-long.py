from pathlib import Path
import importlib.util,json,re,statistics
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;root=P/'runtime-collected-r2'
state=json.loads((root/'state.json').read_text());assert state['terminal'] and state['passed'] and not state['failure'] and not state['new_faults'] and state['formal_modules_restored'] and state['services_restored'] and state['taint_after']==0
spec=importlib.util.spec_from_file_location('gst443',HERE.parent/'kernel443/frame-audit.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
source=base.source.replace('def audit_gst(', 'def audit_long(').replace('coarse_bytes=46080):','coarse_bytes=46080,target=120,expected_result=0):').replace('assert len(frames)==120','assert len(frames)==target').replace("assert 'bus-errors=0 result=0' in text", "assert f'bus-errors=0 result={expected_result}' in text")
namespace={'re':re};exec(compile(source,'retained443-variable-consumer-bound','exec'),namespace)
rows=[];physical=0
for name,summary in state['sustained'].items():
 text=(root/name/'client.log').read_text();cancel=summary['intentional_cancellation'];expected=9 if cancel else 0
 # Keep the raw strict failure visible. A separate diagnostic pass may remove
 # only duplicate negative acknowledgements of already-failed observations;
 # it does not turn the transaction into a successful receipt-contract audit.
 receipts={};duplicates=[];filtered=[]
 for index,line in enumerate(text.splitlines()):
  if 'IPE_RECEIPT ' in line:
   v=dict(re.findall(r'([a-z][a-z0-9-]*)=([^ ]+)',line));token=int(v['token'])
   if token in receipts:
    previous=receipts[token]
    assert previous['success']==previous['result']=='0' and v['success']=='0' and v['result']=='-2' and v['trace']=='0'
    assert all(v[k]==previous[k] for k in ['epoch','sof','token'])
    duplicates.append(dict(line=index+1,sof=int(v['sof']),token=token,result=-2));continue
   receipts[token]=v
  filtered.append(line)
 strict_failure=None
 try:namespace['audit_long'](text,'s5kgw1',width=1920,height=1080,stride=1920,coarse_bytes=261120,target=summary['frames'],expected_result=expected)
 except AssertionError:
  assert duplicates;strict_failure='duplicate failed-observation receipts returned -ENOENT'
 row=namespace['audit_long']('\n'.join(filtered)+'\n','s5kgw1',width=1920,height=1080,stride=1920,coarse_bytes=261120,target=summary['frames'],expected_result=expected)
 row.update(raw_strict_receipt_contract_passed=strict_failure is None,raw_strict_failure=strict_failure,duplicate_negative_receipts=duplicates,successful_frame_chain_audited_separately=True,passed=strict_failure is None)
 samples=[tuple(map(int,m)) for m in re.findall(r'GST_IMAGE frame=(\d+) width=(\d+) height=(\d+) bytes=(\d+) pts=(\d+) hash=(\d+) sequence=(\d+) wall-ns=(\d+)',text)]
 assert len(samples)==summary['frames'] and [s[0] for s in samples]==list(range(len(samples)))
 assert all(s[1:4]==(1920,1080,3110400) and s[5]>0 for s in samples)
 assert all(b[4]>a[4] and b[6]>a[6] and b[7]>a[7] for a,b in zip(samples,samples[1:]))
 identities=re.findall(r'APPLICATION_IDENTITY uid=(\d+) euid=(\d+) capeff=(\S+)',text);assert len(identities)==1 and identities[0][:2]==('10000','10000') and int(identities[0][2],16)==0
 app=set(re.findall(r'APPLICATION_PROCESS pid=(\d+)',text));ipa=set(re.findall(r'IPA stats pid=(\d+)',text));assert len(app)==len(ipa)==1 and not app&ipa
 starts=re.findall(r'CAPACITY_START epoch=1 tid=(\d+) status=0 reason=selected active=1 users=1 original=(\S+) selected=(\S+)',text);assert len(starts)==1;tid,original,selected=starts[0]
 assert re.search(r'CAPACITY_STOP epoch=1 tid='+tid+r' status=0 reason=restored active=0 users=0 original='+re.escape(original)+' selected='+re.escape(selected),text)
 executions=[tuple(map(int,m)) for m in re.findall(r'FOCUS_EXECUTION epoch=1 sof=(\d+) valid=1 sample-wall-us=(\d+) sample-cpu-us=(\d+) minor=(\d+) major=(\d+) voluntary=(\d+) involuntary=(\d+) cpu-before=(\d+) cpu-after=(\d+)',text)]
 allowed={int(c) for c in selected.split(',')};assert executions and all(e[7] in allowed and e[8] in allowed for e in executions)
 assert row['queued_images']==summary['ipe_completed'];physical+=summary['ipe_completed']
 gaps=[dict(after_sof=a[6],before_sof=b[6],missing=b[6]-a[6]-1,after_frame=a[0]) for a,b in zip(samples,samples[1:]) if b[6]>a[6]+1]
 def times(values):
  xs=sorted(v/1000 for v in values);return dict(median_ms=round(statistics.median(xs),3),p95_ms=round(xs[min(len(xs)-1,len(xs)*95//100)],3),maximum_ms=round(xs[-1],3))
 dt=samples[-1][4]-samples[0][4]
 row.update(capture=name,uid=10000,effective_capabilities=0,intentional_signal_cancellation=cancel,elapsed_seconds=summary['elapsed_seconds'],pts_span_seconds=round(dt/1e9,3),timestamp_fps=round((len(samples)-1)*1e9/dt,3),wall_fps=round((len(samples)-1)*1e9/(samples[-1][7]-samples[0][7]),3),kernel_sequence_gaps=gaps,missing_sofs=sum(g['missing'] for g in gaps),maximum_pts_interval_ms=round(max((b[4]-a[4])/1e6 for a,b in zip(samples,samples[1:])),3),capacity_restored=True,focus_sample_wall=times([e[1] for e in executions]),focus_sample_thread_cpu=times([e[2] for e in executions]),focus_off_cpu_approx=times([max(0,e[1]-e[2]) for e in executions]))
 conditions=[json.loads(line) for line in (root/name/'conditions.log').read_text().splitlines()];assert conditions[0]['kind']=='configuration' and conditions[-1]['kind']=='finished'
 observed=conditions[1:-1];assert observed and all(s['kind']=='sample' for s in observed)
 zones={}
 for zone,kind in conditions[0]['thermal_types'].items():
  values=[(s['monotonic_ns'],int(s['temperatures_millidegrees'][zone])) for s in observed if s['temperatures_millidegrees'].get(zone) is not None]
  if values:zones[zone]=dict(type=kind,first_c=values[0][1]/1000,last_c=values[-1][1]/1000,minimum_c=min(v for t,v in values)/1000,maximum_c=max(v for t,v in values)/1000)
 row['conditions']=dict(samples=len(observed),observer_cpu_seconds=conditions[-1]['cpu_seconds'],observed_span_seconds=round((observed[-1]['monotonic_ns']-observed[0]['monotonic_ns'])/1e9,3),thermal_zones=zones,not_power_measurement=True)
 if cancel:assert summary['exit_code']==1 and 'exited=1 exit=9 signalled=0' in text and len(samples)<9000
 else:assert len(samples)==9000 and summary['exit_code']==0
 rows.append(row)
s=state['candidate_final_status'];assert s['jobs']==s['completed']==s['direct_completed']==physical and not any(s[k] for k in ['failed','cancelled','first_error','fatal','pinned','orphans','users','running'])
kernel_log_completions=(root/'kernel-log-private.txt').read_text().count('A5 IPE frame completed request=')
assert 0<kernel_log_completions<=physical
lifecycle=json.loads((HERE/'lifecycle-validation.json').read_text());assert lifecycle['passed']
residual=json.loads((HERE/'residual-r2-validation.json').read_text());assert residual['passed']
r=dict(stage=449,rows=rows,r2_ipe_completed=physical,kernel_log_completions_retained=kernel_log_completions,kernel_log_ring_does_not_cover_entire_run=kernel_log_completions<physical,physical_completions_from_final_driver_counters=True,retained_r1_lifecycle_frames=lifecycle['lifecycle_frames'],retained_r1_lifecycle_ipe_completed=lifecycle['lifecycle_ipe_completed'],all_user_consumers_uid10000_capabilities0=True,production448_source_artifacts_and_factory_tuning_reused=True,first_r1_fixed50s_interruption_not_replayed=True,formal440_and_persistent_charging_restored=True,no_new_orphan_proxies=True,new_kernel_faults=0,taint=0,encoded_recording_accepted=False,zero_drop_30fps_accepted=False,power_thermal_acceptance=False,historical441_backlog_closed=False,full_goal_complete=False,successful_image_chains_passed=True,passed=all(row['raw_strict_receipt_contract_passed'] for row in rows))
(HERE/'hardware-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
