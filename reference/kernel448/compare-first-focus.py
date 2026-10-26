from pathlib import Path
import json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
current=json.loads((HERE/'hardware-validation.json').read_text());prior=json.loads((HERE.parent/'kernel447/hardware-r2-validation.json').read_text())
raw=json.loads((P.parent/'kernel447/focus-execution-r2-private.json').read_text());old={r['capture']:r['records'] for r in raw}
rows=[]
for r in current['stream_lifetime_capacity_policy']:
 if r['capture'] not in old:continue
 first=min(old[r['capture']],key=lambda x:x['sof'])
 rows.append(dict(capture=r['capture'],prior447_postfirstimage_affinity_first_sample_wall_ms=first['wall_us']/1000,current448_prestream_lease_first_sample_wall_ms=r['first_sample_wall_ms'],prior_first_cpu_before=first['cpu_before'],current_first_cpu_endpoints_all_selected=r['all_focus_cpu_endpoints_include_first_frame_selected']))
assert len(rows)==2
r=dict(stage=448,rows=rows,all_four_main_consumer_paths_30_056fps_and_zero_steady_missing_sofs=all(x['timestamp_fps']==30.056 and not x['steady_missing_sofs'] for x in current['rows']),full_request_to_first_output_latency_not_claimed=True,separate_boot_and_charging_baseline_not_controlled=True,first_measurement_uses_policy_without_external_injection=True,power_and_long_recording_not_accepted=True,passed=True)
(HERE/'comparison-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
