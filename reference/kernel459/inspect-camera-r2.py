"""Audit cached r2 image receipts independently of post-unplug charging recovery."""
from pathlib import Path
import hashlib,importlib.util,json,re

HERE=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('diagnostic452',HERE.parent/'kernel452/check-diagnostic.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
root=PRIVATE/'kernel452/runtime-collected-r2'
state=json.loads((root/'state.json').read_text())
plan=json.loads((root/'diagnostic-plan-private.json').read_text())
handoff=json.loads((root/'handoff-private.json').read_text())
external=json.loads((PRIVATE/'kernel452/diagnostic-live-r2-1-private.json').read_text())
controller=json.loads((PRIVATE/'kernel459/runtime-collected-r2/result.json').read_text())
health=json.loads((PRIVATE/'kernel459/final-health-after-replug-private.json').read_text())
strict,strict_sha=audit.auditor()
assert state['terminal'] and state['passed'] and state['phase']=='finished'
assert state['diagnostic_final_checks']['passed']
assert state['diagnostic_charging_before']==state['diagnostic_charging_after']==handoff['charging']
assert plan['old444_proxy_preserved'] and plan['only_camera_change_from450']=='libcamera.so.0.7.2'
assert controller['terminal'] and controller['worker_exit_code']==0 and controller['camera_terminal']
assert controller['trace_cleaned'] and not controller['errors'] and not controller['worker_alive_at_controller_end']
assert external['terminal'] and external['worker_exited'] and external['transaction_passed']
assert not external['residual_processes'] and not external['user_directory_exists']
assert external['passed'] is False and 'No data available' in external['current_final_check_failure']
rows=[];physical=0
for name,enabled,expected in [('disabled-120',False,0),('trace-window',True,9)]:
 case=root/name;text=(case/'client.log').read_text()
 frames,gaps=audit.samples(text);summary=state['diagnostic_cases'][name]
 assert len(frames)==summary['frames'] and summary['trace_enabled']==enabled
 result=strict(text,'s5kgw1',width=1920,height=1080,stride=1920,
               coarse_bytes=261120,target=len(frames),expected_result=expected)
 assert result['source_delivered_successful_images']==summary['ipe_completed']
 assert f'exited=1 exit={expected} signalled=0' in text and 'FIXTURE_RESTORATION result=0' in text
 assert re.findall(r'APPLICATION_IDENTITY uid=(\d+) euid=(\d+) capeff=(\S+)',text)==[('10000','10000','0000000000000000')]
 monitor=json.loads((case/'monitor-private.json').read_text());identity=monitor['identity']
 assert monitor['passed'] and monitor['consumed_frames']==len(frames)
 assert identity['passed'] and identity['actual_candidate_core_mapping'] and identity['actual_ipa_module_mapping']
 assert identity['uid']==10000 and identity['effective_capabilities']==0
 assert identity['actual_ipa_exe_sha256']==plan['common_payload']['proxy/camss_ipa_proxy']=='c7887708377b92b167d917173cb2840a78e437a773985fa087ef980bd382038c'
 assert identity['core_sha256_verified_before_start']==plan['common_payload']['lib/libcamera.so.0.7.2']=='e6a90a0699fa62a2c00a03a053bd93d8449450757301bbf7b3804978ceb073d6'
 assert not gaps and monitor['first_gap'] is None
 assert monitor['whole_log_rereads']==0 and not monitor['conditions_observer_used']
 assert monitor['maximum_read_bytes']<=262144 and monitor['maximum_partial_bytes']<=8192
 starts=re.findall(r'CAPACITY_START epoch=1 tid=(\d+) status=0 reason=selected active=1 users=1 original=(\S+) selected=(\S+)',text)
 assert len(starts)==1;tid,original,selected=starts[0]
 assert re.search(r'CAPACITY_STOP epoch=1 tid='+tid+r' status=0 reason=restored active=0 users=0 original='+re.escape(original)+' selected='+re.escape(selected),text)
 allowed=set(map(int,selected.split(',')))
 executions=[tuple(map(int,m)) for m in re.findall(r'FOCUS_EXECUTION epoch=1 sof=(\d+) valid=1 .*cpu-before=(\d+) cpu-after=(\d+)',text)]
 consumed={frame[6] for frame in frames};assert consumed<={item[0] for item in executions}
 assert all(before in allowed and after in allowed for sof,before,after in executions if sof in consumed)
 files=list((case/'captures').iterdir())
 if enabled:
  assert monitor['stop_reason']=='90s_bound' and monitor['stop_signal']['via_pidfd']
  assert monitor['stop_signal']['signal']=='SIGINT' and 90e9<=monitor['stop_signal']['sent_ns']-monitor['launched_ns']<=90.5e9
  assert len(files)==1 and sha(files[0])==summary['trace_export']['sha256']
  trace,records=audit.parse_trace(files[0].read_text())
  result.update(trace=trace,stop_reason=monitor['stop_reason'])
 else:assert len(frames)==120 and not files
 result.update(name=name,consumed_sequence_gaps=gaps,capacity_restored=True,actual_old_proxy_verified=True)
 physical+=summary['ipe_completed'];rows.append(result)
final=state['candidate_final_status']
assert final['jobs']==final['completed']==final['direct_completed']==physical
assert not any(final[k] for k in ['failed','cancelled','first_error','fatal','pinned','orphans','users','running'])
assert not state['after_status']['running'] and not state['after_status']['users']
assert not any(state['after_core'][k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','mapped_bytes','ipe_dma_pending','request_fw_mapped','imported_buffers','watchdogs','cleanup_error','pc_error'])
report=dict(stage=459,window_id=plan['window_id'],raw_strict_auditor_sha256=strict_sha,
 rows=rows,physical_ipe_completed=physical,consumed_images=sum(x['frames'] for x in state['diagnostic_cases'].values()),
 receipt_filter_used=False,raw_image_receipts_passed=True,same_sof_history_and_parameter_math_passed=True,
 transaction_restore_before_later_unplug_passed=True,external_worker_exit_no_residual_passed=True,
 external_final_charging_check_passed=False,post_unplug_health=health['health_audit'],
 overall_acceptance_passed=False,root_cause_proven=False,zero_drop_30fps_acceptance=False,
 inputs_sha256={str(p.relative_to(PRIVATE)):sha(p) for p in [root/'state.json',root/'handoff-private.json',PRIVATE/'kernel452/diagnostic-live-r2-1-private.json',PRIVATE/'kernel459/runtime-collected-r2/result.json',PRIVATE/'kernel459/final-health-after-replug-private.json']},
 audit_completed=True)
(PRIVATE/'kernel459/camera-r2-audit-private.json').write_text(json.dumps(report,indent=2)+'\n')
public=dict(report);public['post_unplug_health']={k:v for k,v in report['post_unplug_health'].items() if k!='manifest_sha256'}
(HERE/'camera-r2-validation.json').write_text(json.dumps(public,indent=2)+'\n')
print(json.dumps({k:v for k,v in public.items() if k not in ['rows','inputs_sha256','post_unplug_health']},indent=2))

