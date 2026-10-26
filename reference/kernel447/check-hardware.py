"""Reuse the strict main consumer audit and quantify CPU versus elapsed sampling."""
from pathlib import Path
import contextlib,io,json,re,statistics
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
source=(HERE.parent/'kernel446/check-hardware.py').read_text().replace('stage=446','stage=447')
a=source.index('other=[]\n');z=source.index("s=state['candidate_final_status'];",a);source=source[:a]+source[z:]
source=source.replace('other_cameras_and_af=other,compatibility=compatibility,cached_phone_focus_benchmarks=benchmarks,','').replace('other_three_stock_profiles_unchanged=True,','')
with contextlib.redirect_stdout(io.StringIO()):exec(compile(source,str(HERE/'check-hardware.py'),'exec'))
report=HERE/'hardware-validation.json';result=json.loads(report.read_text())
observations=[json.loads(line) for line in (root/'cpu-observations.log').read_text().splitlines()]
assert observations[0]['kind']=='configuration' and observations[-1]['kind']=='finished'
config=observations[0];samples=observations[1:-1];assert samples and all(s['kind']=='sample' for s in samples)
assert all(b['monotonic_ns']>a['monotonic_ns'] for a,b in zip(samples,samples[1:]))
assert observations[-1]['samples']==len(samples)
cpu_policy={int(c):name for name,p in config['policies'].items() for c in p['related_cpus'].split()}
assert cpu_policy
private=[]
for row in result['rows']:
 text=(root/row['capture']/'client.log').read_text();queued={int(s) for s in re.findall(r'IPE_TONE_QUEUE epoch=1 sof=(\d+)',text)}
 executions={};timestamps={}
 pattern=r'FOCUS_EXECUTION epoch=1 sof=(\d+) valid=(\d+) sample-wall-us=(\d+) sample-cpu-us=(\d+) minor=(\d+) major=(\d+) voluntary=(\d+) involuntary=(\d+) cpu-before=(\d+) cpu-after=(\d+)'
 for line in text.splitlines():
  m=re.search(pattern,line)
  if not m:continue
  sof,valid,wall,cpu,minor,major,voluntary,involuntary,before,after=map(int,m.groups())
  assert sof not in executions and valid==1 and wall>=cpu-20 and before in cpu_policy and after in cpu_policy
  stamp=re.match(r'\[(\d+):(\d+):(\d+)\.(\d{9})\]',line);assert stamp
  h,mn,s,ns=map(int,stamp.groups());at=((h*60+mn)*60+s)*1000000000+ns
  nearest=min(samples,key=lambda sample:abs(sample['monotonic_ns']-at))
  assert abs(nearest['monotonic_ns']-at)<300000000
  record=dict(sof=sof,wall_us=wall,cpu_us=cpu,off_cpu_approx_us=max(0,wall-cpu),minor=minor,major=major,voluntary=voluntary,involuntary=involuntary,cpu_before=before,cpu_after=after,log_monotonic_ns=at,nearest_observer_ns=nearest['monotonic_ns'],reported_khz_nearby={p:nearest['reported_scaling_khz'][p] for p in {cpu_policy[before],cpu_policy[after]}})
  executions[sof]=record
 assert queued<=set(executions)
 phases={int(s):int(us) for s,us in re.findall(r'FOCUS_TIMING epoch=1 sof=(\d+) sync-start-us=\d+ map-us=\d+ sample-us=(\d+)',text)}
 assert all(phases[s]==executions[s]['wall_us'] for s in queued)
 records=[executions[s] for s in sorted(queued)];private.append(dict(capture=row['capture'],records=records))
 wall=sum(r['wall_us'] for r in records);cpu=sum(r['cpu_us'] for r in records)
 def metric(key):return metrics([r[key] for r in records])
 row['execution']=dict(sample_wall=metric('wall_us'),sample_thread_cpu=metric('cpu_us'),sample_off_cpu_approx=metric('off_cpu_approx_us'),aggregate_thread_cpu_fraction=round(cpu/wall,4),minor_faults=sum(r['minor'] for r in records),major_faults=sum(r['major'] for r in records),voluntary_switches=sum(r['voluntary'] for r in records),involuntary_switches=sum(r['involuntary'] for r in records),cpu_endpoint_migrations=sum(r['cpu_before']!=r['cpu_after'] for r in records),cpu_endpoint_counts={str(c):sum(r['cpu_before']==c for r in records) for c in sorted(cpu_policy)},wall_over33ms=[dict(r) for r in records if r['wall_us']>33000])
 consumed=[int(s) for s in re.findall(r'GST_IMAGE .* sequence=(\d+) wall-ns=',text)];assert len(consumed)==120
 steady=[executions[s] for s in consumed[8:]]
 row['steady_execution']=dict(frames=len(steady),wall=metrics([r['wall_us'] for r in steady]),thread_cpu=metrics([r['cpu_us'] for r in steady]),off_cpu_approx=metrics([r['off_cpu_approx_us'] for r in steady]),over33ms_sofs=[r['sof'] for r in steady if r['wall_us']>33000])
 if staged.get('experiment_mode')=='big-cpu-control':
  affinity=json.loads((root/row['capture']/'affinity-private.log').read_text());assert affinity['only_camera_manager_thread'] and affinity['before']==list(range(8)) and affinity['during']==[4,5,6,7]
  assert state['captures'][row['capture']]['thread_affinity_experiment']['target_thread_gone_after_exit']
  assert all(r['cpu_before'] in affinity['during'] and r['cpu_after'] in affinity['during'] for r in steady)
  row['thread_affinity_control']=dict(mask=[4,5,6,7],steady_endpoints_all_within_mask=True,target_thread_gone_after_exit=True,global_cpu_policy_changed=False)
 for r in row['execution']['wall_over33ms']:
  r.pop('log_monotonic_ns');r.pop('nearest_observer_ns')
(P/('focus-execution-'+attempt+'-private.json')).write_text(json.dumps(private,indent=2)+'\n')
policies={name:dict(**p,reported_khz_observed=sorted({int(s['reported_scaling_khz'][name]) for s in samples if s['reported_scaling_khz'][name] is not None})) for name,p in config['policies'].items()}
observer=observations[-1];result.update(diagnostic_only=True,unchanged446_numeric_contract_reused=True,cpu_policies_read_only=policies,observer_samples=len(samples),observer_cpu_seconds=observer['cpu_seconds'],observer_elapsed_seconds=round(observer['elapsed_ns']/1e9,3),cpu_frequency_samples_are_reported_policy_values_not_cycle_counts=True,off_cpu_difference_includes_measurement_overhead_and_interrupt_or_scheduling_wait=True,faults_count_the_sample_interval_not_mmap_syscall=True)
result['experiment_mode']=staged.get('experiment_mode','observe')
report.write_text(json.dumps(result,indent=2)+'\n');(HERE/f'hardware-{attempt}-validation.json').write_text(report.read_text());print(json.dumps(result,indent=2))
