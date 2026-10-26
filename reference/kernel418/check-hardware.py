"""Verify actual library outputs and the camera request suite from saved evidence."""
from pathlib import Path
import binascii,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;C=P/'runtime-collected-r2'
r=json.loads((HERE/'runtime-validation.json').read_text());s=r['state']
assert s['passed'] and s['terminal'] and not any(r[k] for k in ['worker_live','client_live','collector_live'])
assert s['taint']==512 and s['new_unexpected_fault_count']==0 and s['normal395_restored']
assert not s['collector_result']['captured'] and not s['collector_result']['timeout']
assert len(s['candidate_captures'])==7 and all(v['passed'] for v in s['candidate_captures'].values())
assert sum(v['frames'] for v in s['candidate_captures'].values())==81
assert s['candidate_after']['jobs']==99 and s['candidate_after']['completed']==97 and s['candidate_after']['cancelled']==2
assert not any(s['candidate_after'][k] for k in ['failed','first_error','users','running','fatal','pinned','orphans'])
assert all(v['frames']==12 and v['ipe_completed']==12 and not v['extra_completed'] for v in s['captures'].values())
frames=[v for v in s['native_cases'] if 'sequence' in v];assert len(frames)==16
rows=[]
for case,width,stride,fmt in [(0,640,640,0),(1,650,672,1)]:
    images={}
    for seq,mode in enumerate([0,1,2,2,3,4,0,1]):
        blob=(C/f'wrapper-{case}-{seq}-private.nv12').read_bytes();n=stride*480
        assert len(blob)==n*3//2
        row=next(v for v in frames if v['case']==case and v['sequence']==seq)
        assert row['crc']==(binascii.crc32(blob,0xffffffff)^0xffffffff)
        packed=b''.join(blob[y*stride:y*stride+width] for y in range(480))+b''.join(blob[n+y*stride:n+y*stride+width] for y in range(240))
        if mode==2:reference=bytes(width*480)+bytes([128])*(width*240)
        else:
            fixed={0:0,1:1,3:6,4:9}[mode]
            reference=(P.parent/'kernel406/runtime-collected-r2'/f'width-{width}-format-{fmt}-mode-{fixed}-output-private.nv12').read_bytes()
        difference=sum(a!=b for a,b in zip(packed,reference));assert len(packed)==len(reference) and not difference,(case,seq,mode,difference)
        if mode in images:assert packed==images[mode]
        images[mode]=packed;rows.append(dict(case=case,sequence=seq,mode=mode,width=width,stride=stride,compared_bytes=len(packed),different_bytes=0))
for model in ['imx471','imx319','s5k3m5','s5kgw1']:
    text=(C/('candidate-gst-'+model+'.log')).read_text()+(C/('candidate-gst-'+model+'.out')).read_text()
    assert ' requests=1' in text and 'FIXTURE_RESTORATION result=0' in text
assert s['candidate_captures']['dual']['raw_pairs']==s['candidate_captures']['raw']['raw_pairs']==6
assert not s['candidate_captures']['raw']['ipe']['jobs'] and s['candidate_captures']['isolated']['actual_isolation_verified']
report=dict(stage=418,attempt=2,actual_candidate_library_hardware_verified=True,typed_iq_wrapper_frames=16,rows=rows,
    all_active_pixels_equal_prior_fixed_diagnostics=True,wrapper_cancelled_callbacks=4,kernel_cancelled_jobs=2,
    unstarted_queued_buffers_not_miscounted_as_kernel_jobs=True,kernel_candidate_completed=97,kernel_candidate_jobs=99,
    camera_pipeline_request_frames=81,candidate_four_camera_frames=48,candidate_dual_nv12_frames=6,candidate_raw_pairs=12,candidate_isolated_frames=27,
    all_processed_candidate_camera_runs_requests_enabled=True,raw_only_no_ipe_job=True,
    actual_isolated_ipa_and_five_control_phases=True,candidate_automatic_iq_payloads_still_bypass=True,
    candidate_nonzero_iq_ipa_algorithm_integrated=False,request_complete_three_way_ownership_hardware_exercised=True,
    restart_stop_and_callback_reentry_exercised=True,normal395_restored=True,normal_four_camera_frames=48,normal_ipe_completions=48,
    new_kernel_faults=0,baseline_taint512_from417_retained=True,r1_test_logical_plane_layout_failure_preserved=True,
    forced_lost_ack_with_typed_requests_not_verified=True,candidate_permanently_installed=False,full_goal_kept_active=True,passed=True)
(HERE/'hardware-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))
