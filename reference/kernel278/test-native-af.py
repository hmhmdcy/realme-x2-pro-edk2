"""Exercise real libcamera AF, with application code limited to standard controls."""
from pathlib import Path
import ast,hashlib,json,shlex
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((R/'package-install-validation.json').read_text())['packages_verified']
proof=json.loads((R/'af-probe-build-validation.json').read_text());response=P/'native-af-r1-response-private.log';assert not response.exists()
raw=(P/'af-native278-r2').read_bytes();assert hashlib.sha256(raw).hexdigest()==proof['binary_sha256']
remote='/run/samurai-camera278-probes/af-native278-r2'
upload="from pathlib import Path;import hashlib,sys;p=Path(%r);b=sys.stdin.buffer.read();assert hashlib.sha256(b).hexdigest()==%r;p.parent.mkdir(mode=0o755,exist_ok=True);assert not p.exists();p.write_bytes(b);p.chmod(0o755)"%(remote,proof['binary_sha256'])
host.ssh('python3 -c '+shlex.quote(upload),input=raw,timeout=15)
t=ast.parse((R.parent/'kernel276/test-manager-lifetime.py').read_text());n=next(n for n in t.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='code' for x in n.targets) and isinstance(n.value,ast.Call))
code=ast.literal_eval(n.value.func.value);code=code[:code.index('save();report={}')].replace('k276-manager-lifetime-r1','k278-native-af-r1')
code+='\nBINARY_SHA='+repr(proof['binary_sha256'])+'\n'+r'''
import re,statistics
save();runs=[];public=[]
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k276-work/boot-id-private.txt').read_bytes()
 assert health()['passed']
 binary='/run/samurai-camera278-probes/af-native278-r2';assert hashlib.sha256(Path(binary).read_bytes()).hexdigest()==BINARY_SHA
 sensor=next('/dev/'+p.name for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()=='s5kgw1 6-0010')
 lens=next('/dev/'+p.name for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()=='lc898219xi 6-0072')
 user=pwd.getpwuid(10000)
 def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
 env=dict(PATH='/usr/bin:/bin',HOME=user.pw_dir,USER=user.pw_name,LIBCAMERA_LOG_LEVELS='*:WARN,SimplePipeline:DEBUG')
 q=subprocess.run([binary,'--support'],capture_output=True,preexec_fn=demote,env=env,timeout=25)
 (root/'new-support-private.json').write_bytes(q.stdout);(root/'new-support-stderr-private.log').write_bytes(q.stderr)
 assert q.returncode==0 and json.loads(q.stdout)==dict(af_mode=True,af_trigger=True,af_state=True)
 time.sleep(2)
 for scenario in ['idle','scan','cancel','retrigger','stop']:
  assert health()['passed'];state.update(state='capture-starting',scenario=scenario);save()
  command=[binary,sensor,'/base/soc@0/cci@ac4a000/i2c-bus@0/camera@10','s5kgw1','s5kgw1 6-0010','rgb','2048','1536','manual',scenario]
  with (root/(scenario+'-capture-private.json')).open('xb') as out,(root/(scenario+'-stderr-private.log')).open('xb') as err:
   proc=subprocess.Popen(command,stdout=out,stderr=err,preexec_fn=demote,env=env)
   state.update(state='capture-live',child_pid=proc.pid,child_start_ticks=Path('/proc',str(proc.pid),'stat').read_text().rsplit(')',1)[1].split()[19]);save();proc.wait(timeout=195)
  assert proc.returncode==0,'Native AF probe failed; inspect existing capture files'
  data=json.loads((root/(scenario+'-capture-private.json')).read_text());frames=data['frames'];assert frames
  assert all(f['sequence']==f['raw_sequence'] and f['timestamp_ns']==f['raw_timestamp_ns'] for f in frames)
  matched=[f for f in frames if f['metadata_focus_fom'] is not None];assert matched and all(f['metadata_focus_fom']==f['focus_fom'] for f in matched)
  assert all((f['metadata_focus_fom'] is not None)==(f['queued_index']%4==0) for f in frames),'Focus snapshot cadence must survive asynchronous processing'
  assert all(abs(f['exposure_us']-32000)<=40 and abs(f['analogue_gain']-1)<.03 for f in frames[12:])
  text=(root/(scenario+'-stderr-private.log')).read_text()
  moves=[dict(serial=int(a),position=int(b),result=int(c),monotonic_ns=int(d)) for a,b,c,d in re.findall(r'Focus command (\d+) position (\d+) result (-?\d+) at (\d+)',text)]
  assert all(208<=m['position']<=926 and m['result'] in ([0,-32] if scenario=='stop' else [0]) for m in moves)
  states=[f['af_state'] for f in frames];assert all(f['af_mode']==1 for f in frames)
  if scenario=='idle':assert set(states)=={0} and not moves
  elif scenario in ['scan','retrigger']:
   assert 1 in states and states[-1]==2 and 3 not in states and len(moves)>=10
   assert min(m['position'] for m in moves)==208 and max(m['position'] for m in moves)==926
   first_focused=next(f for f in frames if f['af_state']==2);assert first_focused['timestamp_ns']>moves[-1]['monotonic_ns']+132000000
   if scenario=='scan':
    assert [m['position'] for m in moves[:9]]==[208,304,400,496,592,688,784,880,926]
    assert any(f['queued_af_trigger']==1 and f['af_state']==2 for f in frames),'Cancel outside an active scan must preserve Focused'
   if scenario=='retrigger':assert all(f['af_state']==0 for f in frames if 24<=f['queued_index']<60)
  elif scenario=='cancel':assert 1 in states and all(f['af_state']==0 for f in frames if f['queued_index']>=24) and 2 not in states
  elif scenario=='stop':assert 1 in states and 2 not in states and 3 not in states
  q=subprocess.run(['v4l2-ctl','-d',lens,'--get-ctrl=focus_absolute'],capture_output=True,text=True,timeout=10);assert q.returncode==0
  position=int(re.search(r'focus_absolute: (\d+)',q.stdout).group(1));assert 208<=position<=926
  terminal=[f['focus_fom'] for f in frames if f['af_state']==2]
  row=dict(scenario=scenario,frames=len(frames),standard_af_controls=True,state_values=sorted(set(states)),final_af_state=states[-1],
   same_request_raw_rgb=True,metadata_focus_samples=len(matched),focus_metadata_matches_same_request_raw=True,moves=moves,
   cached_final_position=position,final_fom_median=statistics.median(terminal) if terminal else None,
   application_search_or_lens_writes=False,hardware_position_feedback_not_available=True)
  if scenario=='scan':row.update(repeated_trigger_during_scan_ignored=True,cancel_after_focus_ignored=True)
  public.append(row);runs.append(data);state.update(state='capture-terminal',completed_scenarios=len(public),child_exit=proc.returncode);save();time.sleep(3);assert health()['passed']
except BaseException:
 error=traceback.format_exc();(root/'failure-private.txt').write_text(error)
finally:
 if proc is not None and proc.poll() is None:
  state.update(state='needs-attention-live-capture',terminal=False);save();raise RuntimeError('Capture remains live: inspect same process before another test')
 time.sleep(3);after=health()
 (root/'summary-private.json').write_text(json.dumps(dict(stage=278,runs=runs,public=public,error=error,health=after),indent=2))
 report=dict(stage=278,runs=public,error=None if error is None else 'See retained private failure',health=after,
  single_auto_af_only=True,continuous_and_manual_distance_not_implemented=True,no_raw_i2c_transfers=True,spectra_hardware_isp_not_implemented=True)
 state.update(state='terminal',terminal=True,exit_code=0 if not error and len(public)==5 and after['passed'] else 1);save();print(json.dumps(report))
'''
compile(code,'native-af278-worker','exec');response.write_bytes(b'SUBMISSION INTENT: inspect k278-native-af-r1 before any retry.\n')
q=host.ssh('python3 -',input=code.encode(),timeout=780,check=False);response.write_bytes(q.stdout+q.stderr);assert q.returncode==0 and q.stdout
d=json.loads(q.stdout);(R/'native-af-r1-validation.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps({k:v for k,v in d.items() if k not in ['health','runs']},indent=2));print(json.dumps([dict(scenario=r['scenario'],frames=r['frames'],states=r['state_values'],final_state=r['final_af_state'],moves=len(r['moves']),position=r['cached_final_position'],final_fom=r['final_fom_median']) for r in d['runs']],indent=2));print('Final idle:',d['health']['passed'])
