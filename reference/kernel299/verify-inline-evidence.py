"""Independently cross-check application requests, SOF events, parameters and bundle bytes."""
from pathlib import Path
import hashlib,json,re
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
report=json.loads((HERE/'inline-capture-r3-validation.json').read_text());assert report['passed']
poll=json.loads((P/'inline-r3-poll-private.json').read_text());assert poll['state']['terminal'] and not poll['matching_worker_live'] and not poll['matching_child_live']
q=host.ssh('cat /var/lib/samurai/k299-inline-r3/capture-private.log',timeout=20)
(P/'inline-r3-capture-private.log').write_bytes(q.stdout);text=q.stdout.decode()
applications={};pairs={};events={};acks={};epoch=None
for line in text.splitlines():
 match=re.search(r'APPLICATION_BEGIN epoch=(\d+)',line)
 if match:epoch=int(match[1])+1
 match=re.search(r'APPLICATION_FRAME number=(\d+) request=(\d+) sequence=(\d+) timestamp=(\d+) status=(\d+) bytes=(\d+) hash=(\d+) first_plane_min=(\d+) first_plane_max=(\d+)',line)
 if match:
  assert epoch is not None
  n,request,sequence,timestamp,status,nbytes,fingerprint,low,high=map(int,match.groups())
  key=(epoch,request);assert key not in applications and status==0 and timestamp>0 and nbytes==115200 and low<high
  applications[key]=dict(sequence=sequence,timestamp=timestamp)
 match=re.search(r'Pair epoch=(\d+) sof=(\d+) request=(\d+) population=(\d+) mean=([\d.e+-]+) parameters-acknowledged=(\d+)',line)
 if match:
  e,sof,request,pop,mean,ack=match.groups();key=(int(e),int(request));assert key not in pairs and int(pop)==499392 and int(ack)==1
  pairs[key]=int(sof)
 match=re.search(r'SOF epoch=(\d+) sequence=(\d+)',line)
 if match:events.setdefault(int(match[1]),[]).append(int(match[2]))
 match=re.search(r'Parameters epoch=(\d+) first-sof=(\d+)',line)
 if match:
  e,sof=map(int,match.groups());assert e not in acks;acks[e]=sof
assert len(applications)==len(pairs)==72 and set(applications)==set(pairs)
for e in [1,2,3]:
 keys=sorted(k for k in applications if k[0]==e);assert len(keys)==24 and acks[e]==0
 assert len(events[e])==len(set(events[e])) and events[e]==sorted(events[e])
 assert all(pairs[k] in events[e] and applications[k]['sequence']==pairs[k] for k in keys)
 assert all(applications[b]['timestamp']>applications[a]['timestamp'] for a,b in zip(keys,keys[1:]))
bundle=json.loads((HERE/'inline-bundle-r2-validation.json').read_text());expected=bundle['files']
code="from pathlib import Path\nimport hashlib,json\nr=Path('/var/lib/samurai/k299-inline-r3/bundle')\nnames="+repr(list(expected))+"\nprint(json.dumps({n:hashlib.sha256((r/n).read_bytes()).hexdigest() for n in names}))\n"
actual=json.loads(host.ssh('python3 -',input=code.encode(),timeout=20).stdout)
assert actual=={n:r['sha256'] for n,r in expected.items()}
out=dict(stage=299,kernel_build=298,run='r3',independent_log_crosscheck_passed=True,application_requests=72,raw_sof_statistic_pairs=72,
 all_pairs_match_observed_sof_events_and_application_sequences=True,per_epoch_unique_requests_and_sofs=True,
 timestamps_strictly_increase_per_epoch=True,all_parameter_acks_first_sof_zero=True,all_pairs_have_parameter_ack=True,
 all72_frames_cpu_dma_sync_and_nonconstant_luma=True,physical_roi_population=499392,
 phone_bundle_files_read_back_and_hash_verified=True,tested_bundle_sha256=bundle['archive_sha256'],
 idle_restored_ms=report['idle_observations'][-1]['elapsed_ms'],graph_and_all_recorded_runtime_state_restored=True,
 no_new_kernel_faults=True,not_system_library_install=True,manual_inline_candidate_only=True,
 full_ipa_automatic_algorithms_and_adversarial_sof_acceptance_not_complete=True)
(HERE/'inline-request-association-validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
