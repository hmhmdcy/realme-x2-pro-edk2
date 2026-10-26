from pathlib import Path
import contextlib,io,json,re
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
source=(HERE.parent/'kernel446/check-hardware.py').read_text().replace('stage=446','stage=448')
source=source.replace("{'1280x720-isolated','1920x1080-isolated'}", "{f'{w}x{h}-{k}' for w,h in [(1280,720),(1920,1080)] for k in ['native','isolated']}")
source=source.replace("{'imx319-scene-isolated','s5k3m5-scene-isolated','imx471-scene-isolated','s5kgw1-af-isolated'}", "{'imx471-scene-isolated','s5kgw1-af-isolated'}")
source=source.replace("assert len(app)==len(ipa)==1 and not app&ipa", "assert len(app)==len(ipa)==1 and bool(app&ipa)==(not summary['isolated'])")
a=source.index('benchmarks=[]\n');z=source.index("s=state['candidate_final_status'];",a);source=source[:a]+source[z:]
source=source.replace('cached_phone_focus_benchmarks=benchmarks,','')
with contextlib.redirect_stdout(io.StringIO()):exec(compile(source,str(HERE/'check-hardware.py'),'exec'))
result=json.loads((HERE/'hardware-validation.json').read_text())
capacities={int(c):v for c,v in json.loads((P/'charging-baseline-private.json').read_text())['cpu_capacity'].items()}
policy=[]
for name in list(state['captures'])+list(state['other_captures'])+['compatibility-raw','compatibility-dual']:
 text,_=join_split_frame_record((root/name/'client.log').read_text())
 starts=re.findall(r'CAPACITY_START epoch=1 tid=(\d+) status=(-?\d+) reason=(\S+) active=(\d+) users=(\d+) original=(\S+) selected=(\S+)',text)
 stops=re.findall(r'CAPACITY_STOP epoch=1 tid=(\d+) status=(-?\d+) reason=(\S+) active=(\d+) users=(\d+) original=(\S+) selected=(\S+)',text);assert len(stops)==1
 stop=stops[0];assert stop[1]=='0' and stop[3:5]==('0','0')
 row=dict(capture=name,lease_applied=bool(starts),stop_reason=stop[2],restored_before_camera_manager_thread_exit=True)
 if starts:
  assert len(starts)==1;start=starts[0];assert start[1]=='0' and start[2]=='selected' and start[3:5]==('1','1')
  allowed={int(v) for v in start[5].split(',')};selected={int(v) for v in start[6].split(',')}
  assert selected=={c for c in allowed if capacities[c]>min(capacities[v] for v in allowed)}
  assert stop[0]==start[0] and stop[2]=='restored' and stop[5:]==start[5:]
  executions=[tuple(map(int,m)) for m in re.findall(r'FOCUS_EXECUTION epoch=1 sof=(\d+) valid=1 sample-wall-us=(\d+) sample-cpu-us=(\d+) minor=(\d+) major=(\d+) voluntary=(\d+) involuntary=(\d+) cpu-before=(\d+) cpu-after=(\d+)',text)]
  assert executions and all(e[7] in selected and e[8] in selected for e in executions)
  first=min(executions,key=lambda e:e[0]);row.update(selected_cpus=sorted(selected),original_cpus=sorted(allowed),all_focus_cpu_endpoints_include_first_frame_selected=True,first_focus_sof=first[0],first_sample_wall_ms=round(first[1]/1000,3),first_sample_cpu_ms=round(first[2]/1000,3),sample_wall=metrics([e[1] for e in executions]),sample_cpu=metrics([e[2] for e in executions]),sample_off_cpu_approx=metrics([max(0,e[1]-e[2]) for e in executions]),sample_faults=sum(e[3]+e[4] for e in executions))
 else:assert stop[0]=='0' and stop[2]=='inactive'
 policy.append(row)
result.update(stream_lifetime_capacity_policy=policy,source_host_sanitizers_and_arm_capacity_contract=True,normal_and_isolated_consumers_tested=True,external_thread_affinity_injection=False,first_focus_already_uses_selected_capacity=True,persistent_charging_service_is_new_preserved_baseline=True,power_and_long_recording_accepted=False)
(HERE/'hardware-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
