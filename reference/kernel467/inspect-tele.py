"""Audit cached tele originals and strict receipts; no device operations."""
from pathlib import Path
import hashlib,importlib.util,json,re
HERE=Path(__file__).resolve().parent;PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel467')
root=PRIVATE/'runtime-collected-r1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
state=json.loads((root/'state.json').read_bytes());plan=json.loads((root/'tele-plan-private.json').read_bytes())
handoff=json.loads((root/'handoff-private.json').read_bytes())
assert state['terminal'] and state['passed'] and not state['failure'] and not state.get('cleanup_failure')
assert state['formal_modules_restored'] and state['services_restored'] and state['tele_final_checks']['passed']
assert state['taint_before']==state['taint_after']==0 and not state['new_faults']
assert state['tele_charging_before']==state['tele_charging_after']==handoff['charging']
assert plan['common_payload']['lib/libcamera.so.0.7.2']=='9b352a12a8825935155106d17b81bb33ac60c4d14d7d2007efaad9e3f06af3af'
assert plan['common_payload']['factory-s5k3m5-private.yaml']=='41cba861b491d583c685e07fdc0e97d635f8922f7132abefa15d0632d4fab0a4'
assert plan['old444_proxy_preserved'] and plan['original440_profile_preserved']
base=load('audit443_for467',HERE.parent/'kernel443/frame-audit.py')
source=base.source
for old,new in [('def audit_gst(', 'def audit_tele('),("model=='s5kgw1'", "model=='s5k3m5'"),('assert len(frames)==120','assert len(frames)==32')]:
    assert source.count(old)==1;source=source.replace(old,new)
namespace={'re':re};exec(compile(source,'retained443-tele32-strict-unfiltered','exec'),namespace)
guard=load('guard463_for467',HERE.parent/'kernel463/guarded-trace.py')
trace_plan=guard.GuardedPlan((root/'probe-private.json').read_bytes(),(root/'selection-private.json').read_bytes(),
    (root/'extra-private.json').read_bytes(),(root/'graph-private.txt').read_bytes())
assert trace_plan.full_role==state['full_role']
evidence=root/trace_plan.name;trace_state=json.loads((evidence/'state.json').read_bytes())
assert trace_state['phase']=='cleaned' and trace_state['unrelated_selected_controls_unchanged'] and not trace_state['errors']
capture=trace_state['capture_attempts'][-1];assert capture['complete'] and capture['online_cpus_unchanged']
trace=(evidence/'trace-private-1.txt').read_text();assert sha(evidence/'trace-private-1.txt')==capture['trace']['sha256']
events=[]
for line in trace.splitlines():
    match=re.match(r'^\s*(.*)-(\d+)\s+\[(\d+)\]\s+\S+\s+(\d+\.\d+):\s+(\w+): (.*)$',line)
    if not match:continue
    comm,pid,cpu,stamp,kind,payload=match.groups()
    if kind not in ['v4l2_qbuf','v4l2_dqbuf','vb2_dqbuf']:continue
    fields={k:int(v) for k,v in re.findall(r'(index|timestamp|sequence|minor) = (\d+)',payload)}
    events.append(dict(event=kind,pid=int(pid),ns=round(float(stamp)*1e9),**fields))
emission=guard.role.check_emission(trace_plan.full_role,events);assert emission==state['full_emission']
dq=[e for e in events if e['event']=='v4l2_dqbuf' and e['minor']==trace_plan.minor]
for event in dq:
    peers=[v for v in events if v['event']=='vb2_dqbuf' and v['pid']==event['pid'] and v['index']==event['index']
        and v['timestamp']//1000*1000==event['timestamp'] and 0<=event['ns']-v['ns']<2_000_000]
    assert len(peers)==1
stats={}
for file in sorted(evidence.glob('stats-private-1-cpu*.txt')):
    values=dict(re.findall(r'^([^:\n]+):\s*(.+)$',file.read_text(),re.M))
    stats[file.stem.rsplit('-',1)[1]]={k:int(values[k]) for k in ['overrun','commit overrun','dropped events']}
assert len(stats)==8 and all(not any(v.values()) for v in stats.values())
rows=[];physical=0
for name,summary in state['sustained'].items():
    text=(root/name/'client.log').read_text();width,height=summary['width'],summary['height']
    assert (width,height) in [(1280,720),(1920,1080)] and summary['frames']==32
    row=namespace['audit_tele'](text,'s5k3m5',width=width,height=height,stride=width,coarse_bytes=123648 if width==1280 else 261120)
    receipts=re.findall(r'IPE_RECEIPT epoch=(\d+) sof=(\d+) token=(\d+) success=([01]) result=(-?\d+) trace=(\d+) pending=(\d+)',text)
    assert len(receipts)==text.count('IPE_RECEIPT ') and len({(v[0],v[2]) for v in receipts})==len(receipts)
    assert all(int(v[4]) in [0,1] and v[3]==v[4] for v in receipts)
    samples=[tuple(map(int,m)) for m in re.findall(r'GST_IMAGE frame=(\d+) width=(\d+) height=(\d+) bytes=(\d+) pts=(\d+) hash=(\d+) sequence=(\d+) wall-ns=(\d+)',text)]
    assert len(samples)==32 and [s[0] for s in samples]==list(range(32))
    assert all(s[1:4]==(width,height,width*height*3//2) and s[5]>0 for s in samples)
    assert all(b[4]>a[4] and b[6]>a[6] and b[7]>a[7] for a,b in zip(samples,samples[1:]))
    times=[((int(h)*60+int(m))*60+int(s))*10**9+int(ns) for h,m,s,ns in re.findall(r'\[(\d+):(\d+):(\d+)\.(\d{9})\]',text)]
    case_dq=[e for e in dq if min(times)<=e['ns']<=max(times)]
    pipeline_tids={int(v) for v in re.findall(r'\] \[(\d+)\] +(?:INFO|DEBUG|WARN|ERROR) CamssVfe ',text)}
    assert case_dq and all(e['pid'] in pipeline_tids for e in case_dq)
    offsets=[]
    for sample in samples:
        matching=[e for e in case_dq if e['sequence']==sample[6]];assert len(matching)==1
        offsets.append(matching[0]['timestamp']-sample[4])
    # Preserve the observed PTS conversion variation. The unique FULL link is
    # established by the case's monotonic interval, pipeline TID and SOF;
    # GST PTS is not asserted to be the original kernel timestamp.
    offset_span=max(offsets)-min(offsets)
    assert re.findall(r'GST_SENSOR width=(\d+) height=(\d+) code=(\d+)',text)==[('2104','1560',str(summary['sensor_mbus_code']))]
    witness=json.loads((root/name/'live-witness-private.json').read_bytes())
    assert witness['passed'] and witness['isolated'] and witness['application']['exe_sha256']==plan['common_payload']['gst-sustained']
    assert {int(v) for v in re.findall(r'APPLICATION_PROCESS pid=(\d+)',text)}=={witness['application']['pid']}
    assert {int(v) for v in re.findall(r'IPA stats pid=(\d+)',text)}=={witness['ipa_pid']}
    guard.role.check_open_fd(trace_plan.full_role,witness['full_fd_observation'],witness['application'])
    starts=re.findall(r'CAPACITY_START epoch=1 tid=(\d+) status=0 reason=selected active=1 users=1 original=(\S+) selected=(\S+)',text)
    assert len(starts)<=1
    if starts:
        tid,original,selected=starts[0]
        assert re.search(r'CAPACITY_STOP epoch=1 tid='+tid+r' status=0 reason=restored active=0 users=0 original='+re.escape(original)+' selected='+re.escape(selected),text)
    else:
        assert 'CAPACITY_STOP epoch=1 tid=0 status=0 reason=inactive active=0 users=0 original=none selected=none' in text
    assert row['queued_images']==summary['ipe_completed'];physical+=summary['ipe_completed']
    gaps=[dict(after=a[6],before=b[6],missing=b[6]-a[6]-1) for a,b in zip(samples,samples[1:]) if b[6]>a[6]+1]
    row.update(capture=name,width=width,height=height,actual_sensor_mode=3,actual_sensor=[2104,1560],
        raw_receipts=len(receipts),receipt_filter_used=False,duplicate_receipts=0,negative_receipts=0,
        all_32_images_match_actual_full_dq=True,gst_pts_kernel_offset_span_ns=offset_span,
        kernel_sequence_gaps=gaps,capacity_lease_active=bool(starts),capacity_released_or_inactive=True,live_isolated_ipa_and_full_fd=True)
    rows.append(row)
assert len(rows)==2
final=state['candidate_final_status'];assert final['jobs']==final['completed']==final['direct_completed']==physical
assert not any(final[k] for k in ['failed','cancelled','first_error','fatal','pinned','orphans','users','running'])
health=json.loads((PRIVATE/'final-health-r1-private.json').read_bytes())
assert health['health_audit']['passed'] and health['health_audit']['manifest_sha256']==handoff['charging']['manifest_sha256']
for key in ['external_worker_exit_verified','formal_notes_verified','trace_instance_absent','actual_restored_uid10000_services_verified','user_directory_absent']:assert health[key]
log=(root/'kernel-log-private.txt').read_text();assert log.strip() and all(line in health['dmesg'] for line in log.splitlines())
report=dict(stage=467,attempt='r1',passed=True,consumed_images=64,physical_ipe_completed=physical,
    successful_math=sum(r['successful_math'] for r in rows),bootstrap=sum(r['bootstrap'] for r in rows),rows=rows,
    strict_raw_unfiltered_receipts_and_same_sof_history=True,reused_audit_sha256=hashlib.sha256(source.encode()).hexdigest(),
    full_role=dict(pixel_entity=trace_plan.full_role['pixel_entity'],actual_fd_witnesses=2,**emission),
    all_full_dq_uniquely_paired_to_vb2=True,all_consumed_images_matched_full_dq=64,trace_stats=stats,
    trace_instance_cleaned=True,unrelated_trace_controls_unchanged=True,formal_stack_packages_resources_services_restored=True,
    charging_r8_preserved=True,new_kernel_faults=0,taint=0,normal_16_9_mode_verified=False,
    tele_independent_ltm_causal_replay_executed=False,encoded_video_or_optical_quality_accepted=False,full_goal_complete=False)
(HERE/'hardware-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
