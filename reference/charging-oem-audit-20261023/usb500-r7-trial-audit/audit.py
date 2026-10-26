"""Offline audit of one completed R7 trial. All outputs stay in this directory."""
from pathlib import Path
from collections import Counter
from decimal import Decimal
import base64,datetime as dt,hashlib,importlib.util,json,re

HERE=Path(__file__).resolve().parent
NONCE='18306f77ab5726a7929b99d2131242353f7a7c45a1f69e24'
TRIAL=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')/('usb500-r7-'+NONCE)
FETCH='fetch-1792747154239432418';D=TRIAL/FETCH
PROFILE=HERE.parent/'usb500-r7-candidate'
sha=lambda raw:hashlib.sha256(raw).hexdigest()

def no_duplicates(pairs):
 r={}
 for k,v in pairs:assert k not in r,'duplicate JSON field '+k;r[k]=v
 return r

def decode(raw):return json.loads(raw,object_pairs_hook=no_duplicates)
def load(path):return decode(Path(path).read_bytes())
def jsonl(path):
 raw=Path(path).read_bytes();assert raw.endswith(b'\n'),'incomplete final JSONL line'
 rows=[decode(line) for line in raw.splitlines()];assert rows
 return rows

def utc_ns(value):
 match=re.fullmatch(r'(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d{1,9}))?(Z|[+-]\d\d:\d\d)',value)
 assert match,'UTC timestamp lacks explicit zone'
 seconds=int(dt.datetime.fromisoformat(match[1]+match[3].replace('Z','+00:00')).timestamp())
 return seconds*10**9+int((match[2] or '').ljust(9,'0'))

def iso(ns):
 sec,nano=divmod(int(ns),10**9)
 return dt.datetime.fromtimestamp(sec,dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')+'.'+f'{nano:09d}'+'Z'

def float_ns(value):return int(Decimal(str(value))*10**9)

def bracket_bounds(envelopes):
 rows=[]
 for name,item in envelopes:
  h=item['host_request_bracket'];remote=float_ns(item['remote_clock']['real'])
  start,end=map(float_ns,(h['real_start'],h['real_end']));assert start<=end
  rows.append({'label':name,'offset_low_ns':remote-end,'offset_high_ns':remote-start,
   'round_trip_seconds':(end-start)/1e9,'host_start_utc':iso(start),'host_end_utc':iso(end)})
 lo=max(x['offset_low_ns'] for x in rows);hi=min(x['offset_high_ns'] for x in rows)
 assert lo<=hi,'clock-offset brackets have no intersection'
 return lo,hi,rows

def correlation(ports,start,end,lo,hi):
 assert start<end
 # Every admissible offset places these complete query intervals in phase.
 certain=[p for p in ports if p['start']>=start-lo and p['end']<=end-hi]
 possible=[p for p in ports if p['start']<=end-lo and p['end']>=start-hi]
 assert certain and ports[0]['start']<=start-hi and ports[-1]['end']>=end-lo
 def counts(rows):return dict(Counter(p['status_name'] for p in rows))
 return {'device_start_utc':iso(start),'device_end_utc':iso(end),'duration_seconds':(end-start)/1e9,
  'host_possible_start_utc_range':[iso(start-hi),iso(start-lo)],
  'host_possible_end_utc_range':[iso(end-hi),iso(end-lo)],
  'all_offset_certain_queries':len(certain),'certain_status_counts':counts(certain),
  'possibly_overlapping_queries':len(possible),'possible_status_counts':counts(possible),
  'certain_current_configuration_values':dict(Counter(str(p['configuration']) for p in certain)),
  'certain_valid_device_descriptors':sum(p['descriptor_valid'] for p in certain),
  'first_certain_sweep':certain[0]['sweep'],'last_certain_sweep':certain[-1]['sweep'],
  'captured_span_covers_outer_phase_bounds':True}

def main():
 parent=load(TRIAL/'parent-result-private.json');gate=load(TRIAL/'host-ready-private.json')
 owned=load(TRIAL/'reader-owned-private.json');request=load(TRIAL/'launch-request-private.json')
 summary=load(TRIAL/'host-reader/summary.json');meta=load(TRIAL/'host-reader/metadata-private.json')
 rawproof=load(HERE/'raw-redecode-result.json')
 assert parent['nonce']==request['nonce']==NONCE and parent['dispatch_count']==request['dispatch_count']==1
 assert parent['reader_exited'] and not parent['reader_watchdog_killed'] and not parent['phone_worker_killed']
 assert parent['launch_exited'] and parent['fetch_exited'] and parent['failure'] is None
 assert gate['owned_handle_checked'] and gate['host_ready']['host_worker_pid']==owned['pid']
 for key in ['pid','handle','start_ticks','exe']:assert gate['reader_proof'][key]==owned[key]
 assert gate['host_ready']['capture_id']=='usb500-r7-'+NONCE and gate['host_ready']['remaining_seconds_at_trigger']>=110
 assert meta['ReadOnly'] and meta['PortCount']==7 and meta['DurationSeconds']==140
 assert meta['CollectorSha256']==sha((PROFILE/'watch-one-hub.ps1').read_bytes())
 assert meta['DecoderSha256']==sha((PROFILE/'UsbHubReadOnly.cs').read_bytes())
 assert rawproof['passed'] and rawproof['all_decoded_fields_match'] and rawproof['responses']==4781
 assert rawproof['host_capture_sha256']==sha((TRIAL/'host-reader/ports-private.jsonl').read_bytes())
 assert rawproof['metadata_sha256']==sha((TRIAL/'host-reader/metadata-private.json').read_bytes())
 assert rawproof['usb_handles_opened']==rawproof['ioctls_issued']==0

 launch=load(TRIAL/'launch-1792747019740690514-receipt-private.json')
 fetched=load(TRIAL/(FETCH+'-receipt-private.json'))
 for tag,envelope in [('launch-1792747019740690514',launch),(FETCH,fetched)]:
  raw=load(TRIAL/(tag+'-stdout-private.json'))
  assert {k:v for k,v in envelope.items() if k!='host_request_bracket'}==raw
  assert (TRIAL/(tag+'-stderr-private.txt')).read_bytes()==b''
 assert fetched['process_state']=='absent'
 assert fetched['receipt']==launch['receipt']==load(D/'launch-receipt-private.json')
 for name,entry in fetched['files'].items():
  original=base64.b64decode(entry['base64'],validate=True)
  assert sha(original)==entry['sha256'] and original==(D/name).read_bytes(),name
 for name,digest in request['reviewed'].items():
  assert sha((D/name).read_bytes())==digest==sha((PROFILE/'device-candidate'/name).read_bytes())
 receipt=fetched['receipt'];config=load(D/'config-private.json');started=load(D/'execution-started-private.json')
 assert int((D/'worker.pid').read_text())==receipt['pid']==started['pid']
 assert receipt['start_ticks']>0 and receipt['worker_sha256']==request['reviewed']['worker.py']
 assert config['host_trigger_nonce']==started['nonce']==NONCE
 assert config['transaction']=='usb500-r7-diagnostic-v1' and config['manifest_sha256']==request['manifest_sha256']
 assert config['guard']==request['guard'] and config['identity']['boot_id']==request['expected_boot']
 prefix='/root/charging-management-20261023/usb500-r7-diagnostic-v1-'+NONCE
 assert receipt['argv']==['python3','-B',prefix+'/worker.py','--worker',prefix]
 assert config['host_ready']==dict(gate['host_ready'],armed_utc=gate['host_ready']['ready_at_utc'])
 assert load(TRIAL/'fetch-parent-stdout-private.json')['terminal_verified']

 phases=jsonl(D/'phases-private.jsonl');frames=jsonl(TRIAL/'host-reader/ports-private.jsonl')
 for key in ['realtime_ns','monotonic_ns','boottime_ns']:
  assert all(type(r[key]) is int for r in phases)
  assert all(a[key]<b[key] for a,b in zip(phases,phases[1:])),key
 assert all(r['host_trigger_nonce']==NONCE for r in phases)
 result=load(D/'result.json')
 assert result['terminal'] and not result['mutating_state_unknown'] and result['pending_child_pid'] is None
 assert result['diagnostic_completed'] and result['restore100_verified'] and result['descriptor100_bound']
 assert result['passed'] is False and result['native500_accepted'] is False and result['configured500_local']
 assert result['power_supply_budget_writes']==0 and result['journal_errors']==[]
 assert result['recovery_error'] is result['final_error'] is None
 assert result['primary_error']=={'phase':'attempt500','error':'RuntimeError: no continuous12s native500 healthy configuration'}
 journal_result=next(r['result'] for r in phases if r['event']=='result')
 assert journal_result=={k:v for k,v in result.items() if k!='journal_errors'}

 writes=[]
 for stage in ['500:unbind','500:power','500:bind','100:unbind','100:power','100:bind']:
  a,= [r for r in phases if r['event']=='sysfs-write-before' and r['stage']==stage]
  b,= [r for r in phases if r['event']=='sysfs-write-after' and r['stage']==stage]
  assert b['returncode']==0 and b['stderr']=='' and a['monotonic_ns']<b['monotonic_ns']
  writes.append({'stage':stage,'start_device_utc':iso(a['realtime_ns']),'end_device_utc':iso(b['realtime_ns']),
   'elapsed_ms':(b['monotonic_ns']-a['monotonic_ns'])/1e6,'returncode':0})
 assert len([r for r in phases if r['event']=='sysfs-write-before'])==len(writes)==6
 assert max(x['elapsed_ms'] for x in writes)<140
 assert [r['args'] for r in phases if r['event']=='network-before']==[
  ['ip','link','set','usb0','up'],['ip','-j','-6','addr','show','dev','usb0']]*2
 assert all(r['returncode']==0 for r in phases if r['event']=='network-after')

 # Inert import of the pinned workspace definitions; never instantiate Device.
 spec=importlib.util.spec_from_file_location('offline_completed_trial',PROFILE/'device-candidate/worker.py')
 worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)
 before=next(r for r in phases if r['event']=='before')
 baseline=before['observation'];worker.accepted(baseline,100)
 env=before['environment'];assert env['manifest_sha256']==config['manifest_sha256']
 assert env['service_sha256']=='61451ffea87cca466dbbb2f1a2c6e7c05d0eee517479e8b019d43b1869355aa4'
 samples=[r for r in phases if r['event']=='sample']
 stats={}
 for ma,expected_count in [(500,55),(100,18)]:
  ss=[r for r in samples if r['power_ma']==ma];assert len(ss)==expected_count
  complete_receiver=[];hardware_health=[];receiver_errors=Counter();hardware_errors=Counter()
  for r in ss:
   o=r['observation'];s=o['sample'];lim=o['limits'];src=o['source']
   assert {'state','sample','registers','notes','openrc_started','limits','source','udc'}<=o.keys()
   assert type(lim['native_ua']) is type(lim['source_budget_ua']) is int
   assert lim['native_ua']==lim['source_budget_ua']==s['budget_ua']==100000
   assert int(src['input_current_limit'])==int(src['current_max'])==100000 and src['online']=='1' and '[SDP]' in src['usb_type']
   assert lim['input_ua']==(o['registers']['00']&127)*50000==(o['registers']['0f']&127)*50000==100000
   assert lim['charge_ua']==250000 and lim['cv_uv']==4362500
   worker.r6.safe_sample(o);worker.r6.unchanged(baseline,o)
   try:worker.r6.healthy(o,allow_full=True)
   except RuntimeError as e:hardware_health.append(False);hardware_errors[str(e)]+=1
   else:hardware_health.append(True)
   assert o['notes']==baseline['notes'],'all three notes retained'
   assert env=={'camera':{'pm':o['state']['camera_pm'],'m2m':o['state']['m2m'],
    'services':sorted([[x['comm'],x['pid'],x['uid']] for x in o['state']['services']])},
    'fault_count_snapshot':env['fault_count_snapshot'],'manifest_sha256':env['manifest_sha256'],'service_sha256':env['service_sha256']}
   if ma==500:assert o['udc']=='addressed'
   try:worker.accepted(o,ma)
   except RuntimeError as e:complete_receiver.append(False);receiver_errors[str(e)]+=1
   else:complete_receiver.append(True)
  gaps=[(b['monotonic_ns']-a['monotonic_ns'])/1e9 for a,b in zip(ss,ss[1:])]
  span=(ss[-1]['monotonic_ns']-ss[0]['monotonic_ns'])/1e9
  assert max(gaps)<2
  if ma==100:
   assert complete_receiver==[False]+[True]*17
   accepted_span=(ss[-1]['monotonic_ns']-ss[1]['monotonic_ns'])/1e9
   # First accepted observed() time is <= its following sample event minus
   # the stable loop's actual pause(.5); last observed() >= last event.
   # This avoids assuming phase-event timestamp == post-fsync io.now().
   observed_lower_bound=(ss[-1]['monotonic_ns']-ss[2]['monotonic_ns'])/1e9+.5
   assert observed_lower_bound>=12
  else:
   assert complete_receiver==[False]*55
   accepted_span=observed_lower_bound=None
  assert hardware_health==[False]+[True]*(len(ss)-1)
  stats[str(ma)]={'samples':len(ss),'first_device_utc':iso(ss[0]['realtime_ns']),'last_device_utc':iso(ss[-1]['realtime_ns']),
   'span_seconds':span,'max_sample_gap_seconds':max(gaps),'udc_counts':dict(Counter(r['observation']['udc'] for r in ss)),
   'exact_stage_receiver_pass_samples':sum(complete_receiver),'receiver_error_counts':dict(receiver_errors),
   'normal_charge_register_readback_pass_samples':sum(hardware_health),
   'initial_snapshot_register_telemetry_mismatch':{'reg08_masked':ss[0]['observation']['registers']['08']&0x18,'desired_enable':ss[0]['observation']['sample']['desired_enable']},
   'accepted_event_streak_span_seconds':accepted_span,'accepted_observed_streak_lower_bound_seconds':observed_lower_bound,
   'accepted_streak_device_utc_range':[iso(ss[1]['realtime_ns']),iso(ss[-1]['realtime_ns'])] if ma==100 else None,
   'raw_native_ua':100000,'effective_source_budget_ua':100000,'physical_input_paths_ua':[100000,100000],
   'gauge_net_current_ua_range':[min(r['observation']['sample']['gauge_current_ua'] for r in ss),max(r['observation']['sample']['gauge_current_ua'] for r in ss)]}
 assert result['samples100']==18
 worker.accepted(result['final_observation'],100);worker.r6.unchanged(baseline,result['final_observation'])
 assert result['final_observation']['notes']==baseline['notes']

 port7=[];status_counts=Counter();query_count=0;frame_gaps=[]
 for i,frame in enumerate(frames):
  assert frame['Sweep']==i+1 and frame['PartialSweep'] is False and len(frame['Ports'])==7
  assert sorted(p['Port'] for p in frame['Ports'])==list(range(1,8))
  assert frame['StartMs']<=frame['EndMs'] and frame['EndMs']-frame['StartMs']<2000
  if i:frame_gaps.append(frame['StartMs']-frames[i-1]['EndMs'])
  for port in frame['Ports']:
   assert 'Error' not in port and port['Decoded']['ExpectedPort']==port['Decoded']['Port']==port['Port']
   assert frame['StartMs']<=port['QueryStartMs']<=port['QueryEndMs']<=frame['EndMs']
   status_counts[f"{port['Port']}:{port['Decoded']['StatusName']}"]+=1;query_count+=1
   if port['Port']==7:
    assert utc_ns(port['Utc'])<=utc_ns(frame['Utc'])
    port7.append({'sweep':frame['Sweep'],'start':utc_ns(port['Utc']),'end':utc_ns(frame['Utc']),
     'status':port['Decoded']['Status'],'status_name':port['Decoded']['StatusName'],
     'configuration':port['Decoded']['Configuration'],'descriptor_valid':port['Decoded']['DescriptorValid']})
 assert len(frames)==summary['Sweeps']==683 and query_count==summary['Queries']==4781
 assert summary['QueryErrors']==0 and dict(status_counts)==summary['StatusCounts']==rawproof['status_counts']
 assert summary['Terminal'] and summary['Failure'] is None and summary['StopReason']=='deadline'
 assert sum(p['status']==5 for p in port7)==0
 assert all(a['start']<b['start'] for a,b in zip(port7,port7[1:]))
 max_host_gap=max((b['start']-a['start'])/1e9 for a,b in zip(port7,port7[1:]))
 assert max_host_gap<.25
 lo,hi,anchors=bracket_bounds([('launch',launch),('fetch',fetched)])
 real_minus_mono=[r['realtime_ns']-r['monotonic_ns'] for r in phases]
 device_clock_variation=max(real_minus_mono)-min(real_minus_mono)
 start500=next(r['realtime_ns'] for r in phases if r['event']=='configured-local' and r['power_ma']==500)
 restore=next(r['realtime_ns'] for r in phases if r['event']=='restore100-start')
 corr=correlation(port7,start500,restore,lo,hi)
 transitions=[]
 for i,p in enumerate(port7):
  if i==0 or p['status']!=port7[i-1]['status']:
   transitions.append({'sweep':p['sweep'],'query_utc':iso(p['start']),'status':p['status_name']})
 evidence={str(p.relative_to(TRIAL)):sha(p.read_bytes()) for p in [TRIAL/'parent-result-private.json',TRIAL/'host-ready-private.json',
  TRIAL/'host-reader/metadata-private.json',TRIAL/'host-reader/summary.json',TRIAL/'host-reader/ports-private.jsonl',
  TRIAL/(FETCH+'-stdout-private.json'),TRIAL/(FETCH+'-receipt-private.json'),D/'phases-private.jsonl',D/'result.json',D/'worker.py',D/'config-private.json']}
 result_summary={'schema':'usb500-r7-trial-audit-v1','audit_passed':True,'passed':False,'trial_nonce':NONCE,
  'diagnostic_completed':True,'native500_accepted':False,'restore100_verified':True,'descriptor100_bound':True,
  'worker_terminal_verified':True,'worker_pid':receipt['pid'],'phone_process_state':'absent','single_dispatch':True,
  'mutating_state_unknown':False,'power_supply_budget_writes':0,
  'local500':{'configfs_max_power_ma':500,'bound_udc':'a600000.usb','all_six_500_100_writes_returned_zero':True,
   'maximum_write_round_trip_ms':max(x['elapsed_ms'] for x in writes),'writes':writes},
  'device_samples':stats,'final100_fresh_acceptance':True,'three_provider_notes_and_camera_services_preserved':True,
  'host':{'sweeps':683,'get_responses':4781,'query_errors':0,'all_complete_sweeps':True,
   'first_port7_query_utc':iso(port7[0]['start']),'last_complete_sweep_utc':iso(port7[-1]['end']),
   'all_raw_response_decodes_match':True,'port7_status_counts':dict(Counter(p['status_name'] for p in port7)),
   'port7_max_poll_gap_seconds':max_host_gap,'port7_transitions':transitions,
   'explicit_power_status5_observations':0,'hub_bus_powered':rawproof['hub_bus_powered'],
   'configuration_descriptor_read':False,'bmAttributes_or_bMaxPower_from_host_read':False},
  'clock_correlation':{'device_minus_host_offset_ns_intersection':[lo,hi],
   'offset_uncertainty_seconds':(hi-lo)/1e9,'anchors':anchors,
   'device_realtime_minus_monotonic_variation_ns':device_clock_variation,
   'model':'Constant realtime offset over this capture; launcher WSL and Windows reader wall clocks treated as the host UTC basis. One-way delay and a separate WSL-to-Windows offset were not calibrated.',
   'sampling_caveat':'Complete recorded sweeps with bounded polling gaps, not continuous observation between GETs.',
   '500_observation_phase':corr},
  'conclusion':{'native500_not_obtained':True,'device_reached_configured_during_500_samples':False,
   'host_explicit_power_rejection_proven':False,'absence_is_not_a_power_rejection_code':True,
   'failure_reason':'Enumeration/configuration did not complete to a native500 grant in this bounded attempt; host power-rejection cause remains unproven.'},
  'audit_scope':'Existing cached trial only; no device/SSH/USB/SDK action; no configuration-descriptor GET or physical/icon acceptance added.',
  'audit_code_sha256':sha(Path(__file__).read_bytes()),
  'evidence_sha256':evidence}
 (HERE/'usb500-r7-result.json').write_text(json.dumps(result_summary,indent=2)+'\n')
 print(json.dumps({'audit_passed':True,'runtime500_passed':False,'device_samples':{k:v['samples'] for k,v in stats.items()},
  'host_sweeps':len(frames),'restore100_span_seconds':stats['100']['span_seconds'],'clock_certain500_statuses':corr['certain_status_counts']},indent=2))

if __name__=='__main__':main()
