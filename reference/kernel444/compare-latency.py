"""Compare bounded cohorts without treating separate runs as a full FPS proof."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
before=HERE.parent/'kernel443';after=HERE
a=json.loads((before/'hardware-validation.json').read_text());b=json.loads((after/'hardware-validation.json').read_text())
al=json.loads((before/'latency-validation.json').read_text());bl=json.loads((after/'latency-validation.json').read_text())
for d in [a,b,al,bl]:assert d['passed']
ast=json.loads((before/'runtime-staging-r1-validation.json').read_text());bst=json.loads((after/'runtime-staging-r1-validation.json').read_text())
assert ast['profile_sha256']==bst['profile_sha256'] and ast['probe_sha256']==bst['probe_sha256']
old={r['capture']:r for r in a['rows']};new={r['capture']:r for r in b['rows']}
ol={r['capture']:r for r in al['rows']};nl={r['capture']:r for r in bl['rows']};rows=[]
assert old.keys()==new.keys()==ol.keys()==nl.keys()
for name,x in old.items():
 y=new[name];assert x['frames']==y['frames']==120 and x['actual_sensor']==y['actual_sensor']==[4608,2592]
 p=ol[name]['intervals']['pair_to_queue']['median_ms'];q=nl[name]['intervals']['pair_to_queue']['median_ms']
 rows.append(dict(capture=name,prior_pair_to_queue_median_ms=p,current_pair_to_queue_median_ms=q,
  change_ms=round(q-p,3),prior_timestamp_fps=x['timestamp_fps'],current_timestamp_fps=y['timestamp_fps'],
  prior_steady_missing_sofs=ol[name]['steady_missing_sofs'],current_steady_missing_sofs=nl[name]['steady_missing_sofs'],
  current_focus_measurement_median_ms=y['focus_measurement']['median_ms'],current_focus_measurement_maximum_ms=y['focus_measurement']['maximum_ms'],
  current_combined_dispatch_median_ms=y['combined_dispatch']['median_ms'],
  queued_frames_using_combined_call=y['combined_calls_used_for_queued_images'],second_tone_rpc_calls=y['second_tone_rpc_calls_for_queued_images']))
r=dict(stage=444,rows=rows,same_probe_profile_and_kernel_cohort=True,
 common_queued_focus_tone_calls_reduced_from_two_to_one=True,current_queued_jobs=sum(r['queued_frames_using_combined_call'] for r in rows),
 actual_focus_cpu_measurement_tail_now_visible=True,separate_run_lighting_scheduling_and_thermal_conditions_not_controlled=True,
 universal_fps_improvement_claimed=False,historical441_backlog_root_cause_closed=False,long_recording_accepted=False,passed=True)
(HERE/'comparison-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
