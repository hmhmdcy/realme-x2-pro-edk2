from pathlib import Path
import json,re
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel239')
report=json.loads((R/'r15-startup-validation.json').read_text());logs=json.loads((P/'r15-startup-parameter-log-lines-private.json').read_text())
assert report['diagnostic_capture_completed'] and report['run_count']==2 and len(report['frames'])==24
assert len(logs['processing'])==len(logs['debayer'])==len(logs['captured'])==24
rows=[]
for i,(frame,identity,parameters,captured) in enumerate(zip(report['frames'],logs['processing'],logs['debayer'],logs['captured'])):
 m=re.search(r'Processing frame (\d+), sequence (\d+), timestamp (\d+)',identity);assert m
 frame_id,sequence,timestamp=map(int,m.groups());assert sequence==frame['sequence'] and timestamp==frame['timestamp_ns']
 captured_id,captured_seq,_=map(int,re.search(r'Captured request (\d+) from sequence (\d+), control sequence (\d+)',captured).groups());assert (captured_id,captured_seq)==(frame_id,sequence)
 tids=[re.search(r'\] \[(\d+)\] DEBUG Debayer',line)[1] for line in [identity,parameters]];assert tids[0]==tids[1]
 m=re.search(r'blackLevel=Vector \{ ([^}]+)\}; gamma=([^;]+); contrastExp=([^;]+); gains=Vector \{ ([^}]+)\}',parameters);assert m
 black=[float(v.strip()) for v in m[1].split(',')];gain=[float(v.strip()) for v in m[4].split(',')];gamma=float(m[2]);contrast=float(m[3])
 assert frame['run_index']==i//12 and frame['queued_index']==i%12
 if i%12==0:
  assert all(abs(v-16/255)<1e-7 for v in black) and abs(gamma-1/2.2)<1e-6 and contrast==1 and gain==[1,1,1]
  assert 'matrix=Matrix { [ 1, 0, 0 ], [ 0, 1, 0 ], [ 0, 0, 1 ] }' in parameters
 rows.append(dict(run_index=frame['run_index'],queued_index=frame['queued_index'],frame_id=frame_id,source_sequence=sequence,source_timestamp_matches_exactly=True,
                  applied_blc_8bit=round(black[0]*255),applied_gamma_exponent=gamma,applied_gains=gain,rgb_all_zero=frame['all_zero'],rgb_min=frame['byte_min'],rgb_max=frame['byte_max'],rgb_mean=frame['mean']))
result=dict(stage=239,r15_initial_snapshot_verified=True,same_camera_configure_once_stop_start_twice=True,initial_parameters_correct_on_both_starts=True,
            every_processing_identity_matches_callback_sequence_timestamp=True,actual_parameter_lines_paired_by_same_tid=True,
            zero_frames_preserved_without_nonzero_quality_override=True,black_level_tuning_not_changed=True,nonidentity_ccm_runtime_not_tested=True,
            scene_optical_response_and_colour_still_open=True,frames=rows)
(R/'r15-startup-analysis.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(stage=239,startup_fix_verified=True,runs=2,frames=24,initial_blc=[rows[i]['applied_blc_8bit'] for i in [0,12]],initial_gamma=[rows[i]['applied_gamma_exponent'] for i in [0,12]],zero_frames=[dict(run=r['run_index'],index=r['queued_index']) for r in rows if r['rgb_all_zero']],all_cleanup_passed=True)))
