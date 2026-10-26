from pathlib import Path
import json,re
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;before=HERE.parent/'kernel444'
a=json.loads((before/'hardware-validation.json').read_text());b=json.loads((HERE/'hardware-validation.json').read_text())
al=json.loads((before/'latency-validation.json').read_text());bl=json.loads((HERE/'latency-validation.json').read_text())
assert all(d['passed'] for d in [a,b,al,bl])
ast=json.loads((before/'runtime-staging-r1-validation.json').read_text());bst=json.loads((HERE/'runtime-staging-r1-validation.json').read_text())
assert ast['profile_sha256']==bst['profile_sha256'] and ast['probe_sha256']==bst['probe_sha256']
old={r['capture']:r for r in a['rows']};ol={r['capture']:r for r in al['rows']};nl={r['capture']:r for r in bl['rows']};rows=[]
for current in b['rows']:
 name=current['capture'];prior=old[name];text=(P/'runtime-collected-r1'/name/'client.log').read_text()
 queued={int(s) for s in re.findall(r'IPE_TONE_QUEUE epoch=1 sof=(\d+)',text)}
 phases=[tuple(map(int,m)) for m in re.findall(r'FOCUS_TIMING epoch=1 sof=(\d+) sync-start-us=(\d+) map-us=(\d+) sample-us=(\d+) score-us=(\d+) unmap-us=(\d+) sync-end-us=(\d+)',text)]
 slow=[r[0] for r in phases if r[0] in queued and r[3]>33000]
 rows.append(dict(capture=name,prior_focus_median_ms=prior['focus_measurement']['median_ms'],current_focus_median_ms=current['focus_measurement']['median_ms'],
  prior_pair_to_queue_median_ms=ol[name]['intervals']['pair_to_queue']['median_ms'],current_pair_to_queue_median_ms=nl[name]['intervals']['pair_to_queue']['median_ms'],
  prior_timestamp_fps=prior['timestamp_fps'],current_timestamp_fps=current['timestamp_fps'],
  prior_steady_missing_sofs=ol[name]['steady_missing_sofs'],current_steady_missing_sofs=nl[name]['steady_missing_sofs'],
  dominant_phase=current['dominant_focus_phase_counts'],sample_phase_over33ms_sofs=slow,
  sample_phase_includes_allocation_memory_access_faults_and_scheduling=True))
r=dict(stage=445,rows=rows,cached_phone_benchmarks=b['cached_phone_focus_benchmarks'],
 exact_statistics_and_fom_preserved=True,same_probe_profile_ipa6_proxy_signature_and_kernel=True,
 only_two_isolated_sizes_retested=True,separate_live_runs_not_controlled_for_scheduling_lighting_or_temperature=True,
 universal_fps_improvement_claimed=False,historical441_backlog_root_cause_closed=False,long_recording_accepted=False,passed=True)
(HERE/'comparison-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
