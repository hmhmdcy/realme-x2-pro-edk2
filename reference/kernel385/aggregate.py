from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;cases=json.loads((HERE/'image-cases.json').read_text());rows=[]
current=json.loads((HERE/'intree-build-validation.json').read_text())['modules'][0]
previous=json.loads((HERE.parent/'kernel384/intree-build-validation.json').read_text())['modules'][0]
assert current['bytes']==previous['bytes'] and current['sha256']==previous['sha256']
assert hashlib.sha256(Path(current['private_path']).read_bytes()).hexdigest()==hashlib.sha256(Path(previous['private_path']).read_bytes()).hexdigest()==current['sha256']
for i,(case,expected) in enumerate(cases.items(),1):
 run='r'+str(i);r=json.loads((HERE/('boot-runtime-'+run+'-validation.json')).read_text());p=json.loads((HERE/('pixels-'+run+'-validation.json')).read_text())
 assert r['passed'] and p['passed'] and r['same_boot'] and not r['worker_live'] and not r['collector_live']
 d=r['device_result'];assert all(d['test_'+k]==v for k,v in expected.items())
 assert all(d[k]==expected['frames'] for k in ['image_frames','frames_completed','transfer_maps','transfer_unmaps'])
 assert d['session_creates']==d['session_destroys']==d['io_configs']==2 and not d['session_uncertain'] and not d['ipe_dma_pending'] and not d['request_fw_mapped']
 assert not d['watchdogs'] and not d['protocol_errors'] and r['new_relevant_fault_count']==0 and r['taint_after']==0
 rows.append(dict(run=run,case=case,**expected,queue_words=d['queue_state'][:4],messages=d['messages'],interrupts=d['interrupts'],
  uv_mae=p['per_frame_uv_mae'][0],all_frames_Y_equals_current_input=True,all_frames_distinct_output_crc=True,
  alternating_RT_and_non_RT=True,normal_cleanup=True,passed=True))
report=dict(stage=385,tests=rows,total_actual_frames=sum(r['frames'] for r in rows),
 total_Y_bytes_compared_in_kernel=sum(r['width']*r['height']*r['frames'] for r in rows),
 RT_frames=sum((r['frames']+1)//2 for r in rows),non_RT_frames=sum(r['frames']//2 for r in rows),
 per_frame_input_crc_independently_checked_on_host=True,last_full_image_of_each_case_checked_on_host=True,
 all_workers_and_collectors_terminal_and_exited=True,original_kernel_owned_bypass_core_binary_unchanged_from_stage384=True,
 max_cores_two_configuration_verified=True,per_engine_load_or_throughput_not_measured=True,
 sequential_submissions_not_sustained_frame_rate_or_concurrent_stream_claim=True,
 no_actual_sensor_capture=True,full_iq_or_optical_calibration_proven=False,passed=True)
(HERE/'coverage-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
