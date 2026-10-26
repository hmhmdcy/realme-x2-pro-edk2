"""Associate complete single-worker logs by FIFO, keeping metadata/apply distinctions."""
from pathlib import Path
import json,re
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel239')
report=json.loads((R/'fixed-rgb-validation.json').read_text());logs=json.loads((P/'fixed-rgb-parameter-log-lines-private.json').read_text())
assert report['diagnostic_capture_completed'] and not report['passed'] and len(report['frames'])==12
assert len(logs['debayer'])==len(logs['captured'])==12
assert len({re.search(r'\] \[(\d+)\] DEBUG Debayer',line)[1] for line in logs['debayer']})==1
rows=[]
for i,(frame,processing,captured) in enumerate(zip(report['frames'],logs['debayer'],logs['captured'])):
 request,sequence,control_sequence=map(int,re.search(r'Captured request (\d+) from sequence (\d+), control sequence (\d+)',captured).groups())
 assert request==sequence==control_sequence==frame['queued_index']==frame['sequence']==i
 assert abs(frame['exposure_us']-2000)<=20 and frame['analogue_gain']==1
 m=re.search(r'blackLevel=Vector \{ ([^}]+)\}; gamma=([^;]+); contrastExp=([^;]+); gains=Vector \{ ([^}]+)\}',processing);assert m
 black=[float(s.strip()) for s in m[1].split(',')];gains=[float(s.strip()) for s in m[4].split(',')]
 assert len(black)==len(gains)==3 and all(abs(v-black[0])<1e-7 for v in black)
 level=round(black[0]*255);gamma=float(m[2]);assert level in [0,12,16]
 rows.append(dict(queued_index=i,applied_black_level_8bit=level,applied_black_index_256=black[0]*256,applied_gamma_exponent=gamma,applied_gains=gains,
                  ipa_sensor_black_levels=frame['ipa_sensor_black_levels'],ipa_gamma=frame['ipa_gamma'],
                  rgb_min=frame['byte_min'],rgb_max=frame['byte_max'],rgb_mean=frame['mean'],rgb_all_zero=frame['all_zero']))
assert [r['queued_index'] for r in rows if r['rgb_all_zero']]==[1,2,3]
assert rows[0]['applied_black_level_8bit']==0 and rows[0]['applied_gamma_exponent']==1
assert all(rows[i]['applied_black_level_8bit']==16 and abs(rows[i]['applied_gamma_exponent']-1/2.2)<1e-6 for i in [1,2,3])
assert all(rows[i]['applied_black_level_8bit']==12 for i in range(4,12))
result=dict(stage=239,complete_twelve_capture_and_processing_log_entries=True,one_debayer_worker_verified=True,
            association='Complete one-worker FIFO ordinal plus captured request/sequence, not explicit frame IDs in Debayer log',
            fixed_manual_controls_verified=True,actual_debayer_parameters_from_runtime_logs=True,metadata_not_assumed_to_equal_applied_parameters=True,
            initial_default_params_then_blc16_then_blc12_observed=True,zero_frames_match_applied_blc16=True,
            same_frame_raw_data_not_yet_measured=True,strict_nonzero_failure_retained=True,frames=rows)
(R/'fixed-rgb-parameter-analysis.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(stage=239,frames=12,actual_blc_order=[r['applied_black_level_8bit'] for r in rows],zero_indices=[1,2,3],gamma_first=rows[0]['applied_gamma_exponent'],gamma_after=rows[1]['applied_gamma_exponent'],all_cleanup_preserved=True)))
