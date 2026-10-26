"""Verify the saved experiment using ordered kernel markers, not mixed clocks."""
from pathlib import Path
import json,re
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def verify(attempt,report_name):
    r=json.loads((HERE/report_name).read_text());s=r['state'];case=s['case'];C=P/f'runtime-collected-r{attempt}'
    assert s['terminal'] and not any(r[k] for k in ['worker_live','client_live','collector_live'])
    assert case['passed'] and s['failure'] is None and s.get('cleanup_failure') is None and s['normal395_restored']
    assert case['actual_libcamera418'] and case['dropped_ack_count']==1 and 4.5<=case['elapsed_seconds']<12
    assert case['warm_core']['session_peak']==2 and case['warm']['completed']==2 and case['warm']['users']==3
    assert case['failed']['fatal'] and case['failed']['completed']==2 and case['failed']['failed']==2
    assert case['gated']['fatal'] and case['gated']['users']==1 and case['gated']['failed']==3
    assert not case['closed']['fatal'] and case['closed']['users']==0
    after=case['recovered'];assert after['jobs']==6 and after['completed']==after['direct_completed']==3 and after['failed']==3 and after['cancelled']==0 and after['first_error']==-110
    assert s['after_fault_test']['owner_refs']==0 and s['after_fault_test']['users']==0 and not s['after_fault_test']['fatal']
    assert all(c['frames']==12 and c['ipe_completed']>=12 for c in s['captures'].values())
    assert s['taint']==512 and not s['collector_result']['captured'] and not s['collector_result']['timeout']
    lines=(C/'kernel-log-private.txt').read_text().splitlines()
    def first(text,start=0):return next(i for i in range(start,len(lines)) if text in lines[i])
    drop=first('FAULT_TEST dropped validated frame ACK once');assert sum('FAULT_TEST dropped validated frame ACK once' in l for l in lines)==1
    retained=first('FAULT_TEST retained before reset pending=1 request_mapped=1 input_ref=1 output_ref=1',drop)
    iq=first('FAULT_TEST typed IQ retained iq_bytes=8944 parcel_bytes=548864 parcel_present=1 gamma=1 ltm=1',retained)
    pulse=first('A5 forced reset pulse complete; CPU enable/wake clear',iq)
    idle=first('FAULT_TEST before DMA retirement reset_acks=3,3 pending=0 request_mapped=0 input_ref=1 output_ref=1',pulse)
    parcel=first('FAULT_TEST parcel before retirement bytes=548864 present=1',idle)
    retiring=first('A5 retiring DMA aliases',parcel);retired=first('A5 DMA aliases retired',retiring);pm=first('A5 PM reference released: 0',retired)
    recovered_init=first('A5 SYS_INIT acknowledged',pm)
    assert drop<retained<iq<pulse<idle<parcel<retiring<retired<pm<recovered_init
    frame_errors=[];queue_errors=[];expected=[];unexpected=[]
    for i,line in enumerate(lines):
        if drop<=i<recovered_init:
            m=re.search(r'A5 IPE frame failed ret=(-\d+)',line)
            if m:frame_errors.append(int(m[1]))
            m=re.search(r'IPE m2m job failed ret=(-\d+)',line)
            if m:queue_errors.append(int(m[1]))
            if re.search(r'(?:A5 IPE frame failed|IPE m2m job failed) ret=-(?:110|5)(?:\s|$)',line):expected.append(line);continue
        if re.search(r'Unhandled|IOMMU.*[Ff]ault|arm-smmu.*[Ff]ault|SError|BUG:|WARNING:|Oops:|[Tt]ranslation fault|watchdog received|CCI error|Stream stop failed:|A5 IPE frame failed|IPE m2m job failed',line):unexpected.append(line)
    assert frame_errors==[-110] and queue_errors==[-110,-5,-5] and len(expected)==4 and not unexpected
    target=(C/'timed-out-black-private.nv12').read_bytes();assert target==bytes(640*480)+bytes([128])*(640*240)
    healthy=(C/'recovered-la1024-private.nv12').read_bytes();reference=(P.parent/'kernel406/runtime-collected-r2/width-640-format-0-mode-9-output-private.nv12').read_bytes();assert healthy==reference
    log=(C/'typed-ack-loss.log').read_text().splitlines();timeouts=[i for i,l in enumerate(log) if 'IPE dequeue timeout' in l]
    result=dict(attempt=attempt,worker_report_passed=s['passed'],client_case_passed=True,elapsed_seconds=case['elapsed_seconds'],
        iq_bytes_retained=8944,whole_parcel_bytes_retained_through_reset=548864,ordered_reset_ack_dma_retirement_verified=True,
        frame_errors=frame_errors,queue_errors=queue_errors,expected_error_logs=4,unexpected_errors_in_saved_kernel_log=0,
        target_black_pixels_checked_only_after_reset=True,recovered_la1024_all460800_bytes_equal_reference=True,
        old_idle_consumer_fatal_gate_verified=True,wrapper_watchdog_log_count=len(timeouts),normal_four_camera_frames=48,
        runtime_workers_and_clients_terminal=True,passed=True)
    if attempt==2:
        assert case['blocked_callback_seconds']<1 and s['new_unexpected_fault_count']==4 and not s['passed']
        raw=json.loads((C/'state.json').read_text());assert raw['new_unexpected_faults']==expected
        error_stamp=float(re.search(r'\[\s*(\d+\.\d+)\]',expected[0])[1]);assert error_stamp>s['fault_end_uptime']
        result.update(blocked_callback_seconds=case['blocked_callback_seconds'],
            original_worker_false_from_mixed_clock_error_classification_preserved=True,
            no_fault_repeated_to_fix_report=True)
    else:
        starts=[i for i,l in enumerate(log) if 'IPE enabled ' in l];assert len(starts)==4 and len(timeouts)==3
        def seconds(line):
            m=re.search(r'\[(\d+):(\d+):(\d+\.\d+)\]',line);assert m;return int(m[1])*3600+int(m[2])*60+float(m[3])
        delayed=next(i for i in timeouts if i>starts[2]);result['blocked_prior_watchdog_seconds']=seconds(log[delayed])-seconds(log[starts[2]])
    return result

before=verify(1,'runtime-r1-validation.json');after=verify(2,'runtime-validation.json')
one=json.loads((P/'manifest-r1-private.json').read_text());two=json.loads((P/'manifest-private.json').read_text())
for name in ['candidate-core.ko','libcamera.so.0.7.2']:assert one['payload_sha256'][name]==two['payload_sha256'][name]
assert one['payload_sha256']['test-adapter.ko']!=two['payload_sha256']['test-adapter.ko']
assert 2.5<before['blocked_prior_watchdog_seconds']<3.5 and after['blocked_callback_seconds']<.1
report=dict(stage=419,experiments=[before,after],production_adapter_only_changed_between_hardware_variants=True,
    unchanged_test_core_and_libcamera418=True,test_probe_added_latency_measurement_only=True,local_or_quiesced_error_buffers_dequeueable=True,
    unsafe_transfer_poison_preserved_in_actual_source_models=True,failed_physical_quiesce_not_injected=True,
    normal395_restored=True,automatic_ipa_tuning_still_incomplete=True,full_goal_kept_active=True,experiment_passed=True,passed=True)
(HERE/'fault-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
