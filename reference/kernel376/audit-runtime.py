from pathlib import Path
import json,re
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
d=json.loads((HERE/'boot-runtime-validation.json').read_text());assert d['passed'] and d['ipe_session_lifecycle_passed'] and d['same_boot'] and not d['worker_live'] and not d['collector_live']
r=d['device_result'];text=(P/'collected-r1/kernel-log-private.txt').read_text()
markers=['SYS_INIT acknowledged','SYS_PING acknowledged','IPE create acknowledged type=2 active=1','IPE create acknowledged type=3 active=2','IPE destroy acknowledged active=1','IPE destroy acknowledged active=0','SYS_PC_PREP acknowledged','A5 stopped, cooperative=1 block_reset=0 pc_error=0','A5 DMA aliases retired','A5 PM reference released: 0','diagnostic run end ret=0 init=1 ping=1 pc=1','diagnostic overlay remove ret=0','diagnostic module exit end']
positions=[text.index(m) for m in markers];assert positions==sorted(positions)
command_words=(8+16+28*2+44*2+8)//4;message_words=(r['init_bytes']+16+32*2+48*2+12)//4
assert r['queue_state'][:4]==[command_words,command_words,message_words,message_words]==[44,44,61,61]
assert r['session_creates']==r['session_destroys']==r['session_peak']==2 and r['image_sessions']==r['image_frames']==0
m=re.search(r'\[\s*([\d.]+)\].*A5 CPU release',text);n=re.search(r'\[\s*([\d.]+)\].*A5 HFI response=1',text)
report=dict(stage=376,all_markers_ordered=True,two_distinct_simultaneous_ipe_rt_and_non_rt_handles=True,
 both_create_and_destroy_acknowledged=True,remaining_sessions=0,image_frames_submitted=0,image_processing_verified=False,
 full_hfi_lifecycle_verified=True,command_queue_words=command_words,message_queue_words=message_words,
 exact_command_reply_wire_size_accounting_matches_runtime_indices=True,ready_response_latency_ms=round((float(n[1])-float(m[1]))*1000,3),
 same_boot=True,automatic_reset_observed=False,host_reset_sent=False,raw_evidence_private=True,passed=True)
(HERE/'session-runtime-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
