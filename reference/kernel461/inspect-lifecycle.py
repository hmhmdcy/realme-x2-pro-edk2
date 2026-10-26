"""Audit cached 461 artifacts, including all receipts; no device operations."""
from pathlib import Path
import hashlib,importlib.util,json,re

HERE=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel461')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

root=PRIVATE/'runtime-collected-r2'
state=json.loads((root/'state.json').read_bytes());plan=json.loads((root/'lifecycle-plan-private.json').read_bytes())
handoff=json.loads((root/'handoff-private.json').read_bytes())
assert state['terminal'] and state['passed'] and not state['failure'] and not state.get('cleanup_failure')
assert state['formal_modules_restored'] and state['services_restored'] and state['lifecycle_final_checks']['passed']
assert state['taint_before']==state['taint_after']==0 and not state['new_faults']
assert state['lifecycle_charging_before']==state['lifecycle_charging_after']==handoff['charging']
assert plan['common_payload']['lib/libcamera.so.0.7.2']=='9b352a12a8825935155106d17b81bb33ac60c4d14d7d2007efaad9e3f06af3af'
assert plan['common_payload']['proxy/camss_ipa_proxy']=='c7887708377b92b167d917173cb2840a78e437a773985fa087ef980bd382038c'
assert plan['unchanged_449_client'] and plan['original443_profile_preserved'] and plan['old444_proxy_preserved']

# Reuse the actual established six-cycle parser, including dimension-aware
# receipt/history/WB/GTM checks and reading each original NV12 byte sequence.
# Its limited line reassembly preserves every receipt marker; no filtering.
original=(HERE.parent/'kernel449/check-lifecycle.py').read_text()
source=original[original.index("spec=importlib.util.spec_from_file_location('auto441'"):original.index("long=(root/")]
namespace=dict(Path=Path,ast=__import__('ast'),importlib=__import__('importlib'),json=json,re=re,
               HERE=HERE.parent/'kernel449',root=root,state=state)
exec(compile(source,'retained449-lifecycle-no-receipt-filter','exec'),namespace)
rows=namespace['rows'];assert len(rows)==2
total=physical=math=bootstrap=0
for row in rows:
    name=row['capture'];text=(root/name/'client.log').read_text();summary=state['captures'][name]
    raw=re.findall(r'IPE_RECEIPT epoch=(\d+) sof=(\d+) token=(\d+) success=([01]) result=(-?\d+) trace=(\d+) pending=(\d+)',text)
    assert len(raw)==text.count('IPE_RECEIPT ') and len({(v[0],v[2]) for v in raw})==len(raw)
    assert all(int(v[4]) in [0,1] and v[3]==v[4] for v in raw)
    row.update(raw_receipts=len(raw),receipt_filter_used=False,duplicate_receipts=0,negative_result_receipts=0)
    starts=list(re.finditer(r'^LIFECYCLE_BEGIN cycle=(\d+) output=(\d+)x(\d+).*$',text,re.M))
    for i,cycle in enumerate(row['cycles']):
        end=re.search(r'^LIFECYCLE_END cycle='+str(i)+r' status=0$',text[starts[i].start():],re.M)
        part=text[starts[i].start():starts[i].start()+end.end()]
        samples=[tuple(map(int,m)) for m in re.findall(r'ADAPT_FRAME phase=\d+ request=(\d+) sequence=(\d+) timestamp=(\d+)',part)]
        assert len(samples)==cycle['frames']
        assert all(b[1]>a[1] and b[2]>a[2] for a,b in zip(samples,samples[1:]))
        cycle['consumed_sof_gaps']=[dict(after=a[1],before=b[1],missing=b[1]-a[1]-1) for a,b in zip(samples,samples[1:]) if b[1]>a[1]+1]
        math+=cycle['successful_math'];bootstrap+=cycle['bootstrap']
    witness=json.loads((root/name/'live-witness-private.json').read_bytes())
    assert witness['passed'] and witness['isolated']==summary['isolated']
    assert witness['application']['exe_sha256']==plan['common_payload']['lifecycle']
    assert {int(v) for v in re.findall(r'ADAPT_PID value=(\d+)',text)}=={witness['application']['pid']}
    workers={int(v) for v in re.findall(r'IPA stats pid=(\d+)',text)}
    assert witness['ipa_pid'] in workers
    # Reconfigure restarts the isolated IPA. The live /proc witness covers the
    # first cycle; the retained parser checks each subsequent epoch separately.
    if summary['isolated']:assert len(workers)==3
    else:assert workers=={witness['application']['pid']}
    row.update(logged_ipa_processes=len(workers),live_proc_witness_cycles=[0])
    total+=summary['frames'];physical+=summary['ipe_completed']

guard=load('guard463_for461',HERE.parent/'kernel463/guarded-trace.py')
trace_plan=guard.GuardedPlan((root/'probe-private.json').read_bytes(),(root/'selection-private.json').read_bytes(),
    (root/'extra-private.json').read_bytes(),(root/'graph-private.txt').read_bytes())
assert trace_plan.full_role==state['full_role']
for name in state['captures']:
    witness=json.loads((root/name/'live-witness-private.json').read_bytes())
    guard.role.check_open_fd(trace_plan.full_role,witness['full_fd_observation'],witness['application'])
evidence=root/trace_plan.name;trace_state=json.loads((evidence/'state.json').read_bytes())
assert trace_state['phase']=='cleaned' and trace_state['unrelated_selected_controls_unchanged'] and not trace_state['errors']
capture=trace_state['capture_attempts'][-1];assert capture['complete'] and capture['online_cpus_unchanged']
trace=(evidence/'trace-private-1.txt').read_text()
assert sha(evidence/'trace-private-1.txt')==capture['trace']['sha256']
events=[dict(event='v4l2_'+kind,minor=int(minor)) for kind,minor in re.findall(r'\bv4l2_(qbuf|dqbuf):[^\n]*?\bminor\s*=\s*(\d+)',trace)]
emission=guard.role.check_emission(trace_plan.full_role,events);assert emission==state['full_emission']
stats={}
for file in sorted(evidence.glob('stats-private-1-cpu*.txt')):
    values=dict(re.findall(r'^([^:\n]+):\s*(.+)$',file.read_text(),re.M))
    stats[file.stem.rsplit('-',1)[1]]={k:int(values[k]) for k in ['entries','overrun','commit overrun','dropped events','read events']}
assert len(stats)==8 and all(not row['commit overrun'] and not row['dropped events'] for row in stats.values())
health=json.loads((PRIVATE/'final-health-r2-private.json').read_bytes())
assert health['health_audit']['passed'] and health['health_audit']['manifest_sha256']==handoff['charging']['manifest_sha256']
for key in ['external_worker_exit_verified','formal_notes_verified','trace_instance_absent','actual_restored_uid10000_services_verified','user_directory_absent']:assert health[key] is True
log=(root/'kernel-log-private.txt').read_text();assert log.strip()
assert all(line in health['dmesg'] for line in log.splitlines())
assert not re.search(r'messages suppressed|messages dropped|printk.*dropped|Lost \d+ messages',log,re.I)
assert 'start_uptime=time.monotonic()' in (PRIVATE/'lifecycle-prepared-r2/worker.py').read_text()
final=state['candidate_final_status'];assert final['jobs']==final['completed']==final['direct_completed']==physical
assert not any(final[k] for k in ['failed','cancelled','first_error','fatal','pinned','orphans','users','running'])
report=dict(stage=461,attempt='r2',passed=True,consumed_images=total,physical_ipe_completed=physical,
    successful_math=math,bootstrap=bootstrap,rows=rows,raw_unfiltered_receipts_passed=True,
    reused_lifecycle_audit_sha256=hashlib.sha256(source.encode()).hexdigest(),same_sof_pd10_gtm_wb_history=True,
    full_role=dict(pixel_entity=trace_plan.full_role['pixel_entity'],video_node=trace_plan.node,minor=trace_plan.minor,
                   actual_unprivileged_fd_witnesses=2,**emission),trace_instance_cleaned=True,
    unrelated_trace_controls_unchanged=True,trace_stats=stats,trace_overrun=sum(v['overrun'] for v in stats.values()),
    formal_modules_library_packages_services_restored=True,external_worker_exit_and_no_residual_verified=True,
    monotonic_kernel_log_lines=len(log.splitlines()),camera_faults=0,taint=0,fresh_charging_managed_samples=health['health_audit']['sample_count'],
    source_native_allowance_ua=health['health_audit']['native_allowance_after'],charging_limits_preserved=True,
    r1_tool_failure_preserved=True,r1_replayed=False,stop_inside_send_sync_forced_on_hardware=False,
    drop_root_cause_proven=False,long_term_zero_drop_or_full_goal_complete=False,
    unchanged_442_ltm_causal_evidence_reused=True,private_images_and_full_logs_published=False)
(HERE/'lifecycle-r2-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['rows','trace_stats']},indent=2))
