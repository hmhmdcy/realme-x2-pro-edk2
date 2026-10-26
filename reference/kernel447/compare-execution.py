"""Compare the two completed transactions; do not equate this with recording acceptance."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
a=json.loads((HERE/'hardware-r1-validation.json').read_text());b=json.loads((HERE/'hardware-r2-validation.json').read_text())
sa=json.loads((HERE/'runtime-staging-r1-validation.json').read_text());sb=json.loads((HERE/'runtime-staging-r2-validation.json').read_text())
assert all(d['passed'] for d in [a,b,sa,sb]) and a['experiment_mode']=='observe' and b['experiment_mode']=='big-cpu-control'
assert sa['core_sha256']==sb['core_sha256'] and sa['profile_sha256']==sb['profile_sha256']
assert a['cpu_policies_read_only'].keys()==b['cpu_policies_read_only'].keys()
for name,p in a['cpu_policies_read_only'].items():
 for key in ['related_cpus','scaling_governor','scaling_min_freq','scaling_max_freq']:assert p[key]==b['cpu_policies_read_only'][name][key]
prior={r['capture']:r for r in a['rows']};rows=[]
for current in b['rows']:
 p=prior[current['capture']];x=p['steady_execution'];y=current['steady_execution']
 assert current['thread_affinity_control']['steady_endpoints_all_within_mask']
 rows.append(dict(capture=current['capture'],steady_frames_each=112,sample_wall_median_ms_before=x['wall']['median_ms'],sample_wall_median_ms_big=y['wall']['median_ms'],sample_wall_maximum_ms_before=x['wall']['maximum_ms'],sample_wall_maximum_ms_big=y['wall']['maximum_ms'],sample_cpu_median_ms_before=x['thread_cpu']['median_ms'],sample_cpu_median_ms_big=y['thread_cpu']['median_ms'],off_cpu_maximum_ms_before=x['off_cpu_approx']['maximum_ms'],off_cpu_maximum_ms_big=y['off_cpu_approx']['maximum_ms'],sample_over33ms_sofs_before=x['over33ms_sofs'],sample_over33ms_sofs_big=y['over33ms_sofs'],timestamp_fps_before=p['timestamp_fps'],timestamp_fps_big=current['timestamp_fps'],steady_missing_sofs_before=p['steady_missing_sofs'],steady_missing_sofs_big=current['steady_missing_sofs']))
slow=[dict(capture=r['capture'],**f) for r in a['rows'] for f in r['execution']['wall_over33ms']]
assert len(slow)==4 and all(r['minor']==r['major']==r['voluntary']==0 and r['involuntary']>0 and r['cpu_before']==0 for r in slow)
assert all(r['off_cpu_approx_us']>23000 for r in slow)
r=dict(stage=447,rows=rows,unrestricted_slow_sample_frames=slow,total_ipe_completed=a['total_ipe_completed']+b['total_ipe_completed'],two_completed_transactions_same_core_profile_probe_ipa_and_kernel=True,sampling_interval_faults_all_zero=True,preemption_and_capacity_are_material_contributors=True,whole_cost_is_not_proven_to_be_scheduler_only=True,thread_only_affinity_control_after_first_frame=True,first_frame_latency_not_fixed=True,global_cpu_policy_and_thermal_not_modified=True,root441_backlog_closed=False,long_recording_accepted=False,power_or_thermal_acceptance=False,sequential_runs_not_randomized_or_environment_controlled=True,passed=True)
(HERE/'comparison-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
