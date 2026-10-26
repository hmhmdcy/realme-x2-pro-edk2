"""Compare dynamic request pixels with the previously proven fixed diagnostics."""
from pathlib import Path
import binascii,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;C=P/'runtime-collected-r4'
r=json.loads((HERE/'runtime-validation.json').read_text());s=r['state']
assert s['passed'] and s['terminal'] and not any(r[k] for k in ['worker_live','client_live','collector_live'])
assert s['after_native']['jobs']==s['after_native']['completed']==s['after_native']['direct_completed']==16
assert s['after_native']['starts']==s['after_native']['stops']==2
assert s['taint']==s['baseline_taint']==512 and s['new_unexpected_fault_count']==0
rows=[];modes=[0,1,2,2,3,4,0,1]
for case,width,stride,fmt in [(0,640,640,0),(1,650,672,1)]:
    images={}
    for seq,mode in enumerate(modes):
        blob=(C/f'request-{case}-{seq}-private.nv12').read_bytes();n=stride*480
        assert len(blob)==n*3//2
        row=s['native_cases'][case*8+seq]
        assert row['crc']==(binascii.crc32(blob,0xffffffff)^0xffffffff)
        packed=b''.join(blob[y*stride:y*stride+width] for y in range(480))+b''.join(blob[n+y*stride:n+y*stride+width] for y in range(240))
        if mode==2:reference=bytes(width*480)+bytes([128])*(width*240)
        else:
            fixed={0:0,1:1,3:6,4:9}[mode]
            reference=(P.parent/'kernel406/runtime-collected-r2'/f'width-{width}-format-{fmt}-mode-{fixed}-output-private.nv12').read_bytes()
        difference=sum(a!=b for a,b in zip(packed,reference));assert len(packed)==len(reference) and difference==0,(case,seq,mode,difference)
        if mode in images:assert packed==images[mode]
        images[mode]=packed;rows.append(dict(case=case,sequence=seq,mode=mode,width=width,stride=stride,format='NV21' if fmt else 'NV12',compared_bytes=len(packed),different_bytes=difference))
assert all(c['frames']==12 for c in s['captures'].values())
report=dict(stage=417,attempt=4,actual_media_request_hardware_execution=True,frames=16,rows=rows,
    contiguous_requests_switch_bypass_colour_zero_gamma_la2048_la1024=True,
    all_active_pixels_equal_prior_fixed_diagnostic_outputs=True,identical_payload_repeated_and_request_fd_reused=True,
    user_packet_overwritten_after_s_ext_ctrls_and_completed_readback_equal=True,
    output_tail_input_sequence_timestamp_and_control_completion_checked=True,
    direct_controls_missing_payload_invalid_quantized_value_and_interlaced_rejected=True,
    normal395_restored=True,normal_four_camera_application_frames=48,normal_ipe_completions=49,normal_extra_completed=1,
    new_kernel_faults=0,baseline_taint=512,known_failed_r2_warning_retained=True,
    r1_node_enumeration_failure_retained=True,r2_missing_buf_out_validate_failure_retained=True,
    r3_overbroad_la_edge_assertion_failure_retained=True,
    libcamera_request_integration=False,automatic_factory_tuning=False,forced_fault_recovery_with_request_iq=False,
    candidate_permanently_installed=False,full_goal_kept_active=True,passed=True)
(HERE/'pixels-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))
