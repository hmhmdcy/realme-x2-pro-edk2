"""Cross-check both execution modes against raw logs and read-back candidate bytes."""
from pathlib import Path
import hashlib,json,re
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
outcomes=[]
for run,isolated in [('r4',False),('r5',True)]:
 report=json.loads((HERE/f'ipa-capture-{run}-validation.json').read_text());assert report['passed']
 poll=json.loads((P/f'ipa-{run}-poll-private.json').read_text());assert poll['state']['terminal'] and not poll['matching_worker_live'] and not poll['matching_child_live']
 q=host.ssh('cat /var/lib/samurai/k300-ipa-'+run+'/capture-private.log',timeout=20)
 (P/f'ipa-{run}-capture-private.log').write_bytes(q.stdout);text=q.stdout.decode()
 app={};metadata=set();pairs={};events={};decoded=set();acks={};epoch=None;stats_tids=set();handler_tids=set()
 init=re.findall(r'IPA init pid=(\d+)',text);assert len(init)==1
 for line in text.splitlines():
  m=re.search(r'APPLICATION_BEGIN epoch=(\d+)',line)
  if m:epoch=int(m[1])+1
  m=re.search(r'APPLICATION_IPA_METADATA request=(\d+) colour_gains_valid=1',line)
  if m:
   key=(epoch,int(m[1]));assert key not in metadata;metadata.add(key)
  m=re.search(r'APPLICATION_FRAME number=(\d+) request=(\d+) sequence=(\d+) timestamp=(\d+) status=(\d+) bytes=(\d+) hash=(\d+) first_plane_min=(\d+) first_plane_max=(\d+)',line)
  if m:
   n,r,s,t,status,size,fingerprint,lo,hi=map(int,m.groups());key=(epoch,r)
   assert key not in app and status==0 and size==115200 and lo<hi and t>0;app[key]=dict(sequence=s,timestamp=t)
  m=re.search(r'Pair epoch=(\d+) sof=(\d+) request=(\d+) population=(\d+) mean=([\d.e+-]+) parameters-acknowledged=(\d+)',line)
  if m:
   e,s,r,pop,mean,ack=m.groups();key=(int(e),int(r));assert key not in pairs and int(pop)==499392 and int(ack)==1;pairs[key]=int(s)
   tid=re.match(r'^\[[^]]+\] \[(\d+)\]',line);assert tid;handler_tids.add(int(tid[1]))
  m=re.search(r'SOF epoch=(\d+) sequence=(\d+)',line)
  if m:events.setdefault(int(m[1]),[]).append(int(m[2]))
  m=re.search(r'IPA stats pid=(\d+) epoch=(\d+) sof=(\d+) status=0',line)
  if m:
   pid,e,s=map(int,m.groups());assert pid==int(init[0]);decoded.add((e,s))
   tid=re.match(r'^\[[^]]+\] \[(\d+)\]',line);assert tid;stats_tids.add(int(tid[1]))
  m=re.search(r'Parameters epoch=(\d+) first-sof=(\d+)',line)
  if m:e,s=map(int,m.groups());assert e not in acks;acks[e]=s
 assert set(app)==metadata==set(pairs) and len(app)==72
 for e in [1,2,3]:
  keys=sorted(k for k in app if k[0]==e);assert len(keys)==24 and acks[e]==0
  assert events[e]==sorted(set(events[e]))
  assert all(pairs[k] in events[e] and (e,pairs[k]) in decoded and app[k]['sequence']==pairs[k] for k in keys)
  assert all(app[b]['timestamp']>app[a]['timestamp'] for a,b in zip(keys,keys[1:]))
 app_pid=report['application_pids'][0];ipa_pid=int(init[0]);assert (app_pid!=ipa_pid)==isolated
 assert stats_tids and handler_tids and not stats_tids.intersection(handler_tids)
 if not isolated:assert 'signature is valid' in text
 expected=json.loads((HERE/'ipa-bundle-r4-validation.json').read_text())['files']
 code="from pathlib import Path\nimport hashlib,json\nr=Path('/var/lib/samurai/k300-ipa-"+run+"/bundle')\nnames="+repr(list(expected))+"\nprint(json.dumps({n:hashlib.sha256((r/n).read_bytes()).hexdigest() for n in names}))\n"
 actual=json.loads(host.ssh('python3 -',input=code.encode(),timeout=20).stdout);assert actual=={n:v['sha256'] for n,v in expected.items()}
 outcomes.append(dict(run=run,mode='forced-isolated' if isolated else 'signed-threaded',application_requests=72,unique_sof_pairs=72,metadata_frames=72,
  parameter_first_sofs=[acks[e] for e in [1,2,3]],ipa_initializations=1,application_pid=app_pid,ipa_pid=ipa_pid,
  ipa_statistics_thread_ids=sorted(stats_tids),handler_thread_ids=sorted(handler_tids),
  graph_restored=True,idle_restored_ms=report['idle_observations'][-1]['elapsed_ms'],all8_bundle_files_read_back_and_verified=True))
out=dict(stage=300,kernel_build=298,independent_crosscheck_passed=True,execution_modes=outcomes,
 total_verified_application_frames=144,all_pairs_match_application_metadata_raw_sof_and_ipa_decode_events=True,
 module_initialized_once_across_restart_epochs=True,normal_mode_module_signature_accepted=True,no_remaining_recorded_ipa_workers=True,
 manual_candidate_only=True,per_request_controls_sensor_delays_ae_awb_multicamera_iq_not_complete=True)
(HERE/'runtime-association-validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
