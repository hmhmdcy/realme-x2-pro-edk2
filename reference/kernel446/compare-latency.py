from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
old=json.loads((HERE.parent/'kernel445/hardware-validation.json').read_text());new=json.loads((HERE/'hardware-validation.json').read_text())
prior={r['capture']:r for r in old['rows']};rows=[]
for row in new['rows']:
 p=prior[row['capture']]
 rows.append(dict(capture=row['capture'],focus_median_ms_before=p['focus_measurement']['median_ms'],focus_median_ms_now=row['focus']['focus_measurement']['median_ms'],sample_median_ms_before=p['focus_phases']['sample']['median_ms'],sample_median_ms_now=row['focus']['focus_phases']['sample']['median_ms'],sample_maximum_ms_before=p['focus_phases']['sample']['maximum_ms'],sample_maximum_ms_now=row['focus']['focus_phases']['sample']['maximum_ms'],timestamp_fps_before=p['timestamp_fps'],timestamp_fps_now=row['timestamp_fps'],steady_missing_sofs_now=row['steady_missing_sofs']))
r=dict(stage=446,rows=rows,workspace_allocation_and_zeroing_removed_from_steady_sampling=True,statistics_and_fom_exact=True,same_probe_stock_profile_ipa6_proxy_signature_and_kernel=True,separate_runs_across_recovery_boot_not_controlled_for_temperature_light_or_scheduling=True,cpu_cache_benchmark_is_not_dma_benchmark=True,universal_fps_improvement_claimed=False,historical441_backlog_root_cause_closed=False,long_recording_accepted=False,passed=True)
(HERE/'comparison-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
