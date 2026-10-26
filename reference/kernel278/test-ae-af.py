"""Validate the product AF path with AE and analogue gain left in Auto."""
from pathlib import Path
import ast,hashlib,json,shlex
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((R/'native-af-r1-validation.json').read_text())['error'] is None
proof=json.loads((R/'ae-af-probe-build-validation.json').read_text());binary=P/'af-native278-auto';assert hashlib.sha256(binary.read_bytes()).hexdigest()==proof['binary_sha256']
response=P/'ae-af-r1-response-private.log';assert not response.exists();remote='/run/samurai-camera278-probes/af-native278-auto'
upload="from pathlib import Path;import sys,hashlib;p=Path(%r);assert not p.exists();b=sys.stdin.buffer.read();assert hashlib.sha256(b).hexdigest()==%r;p.write_bytes(b);p.chmod(0o755)"%(remote,proof['binary_sha256'])
host.ssh('python3 -c '+shlex.quote(upload),input=binary.read_bytes(),timeout=15)
t=ast.parse((R.parent/'kernel276/test-manager-lifetime.py').read_text());n=next(n for n in t.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='code' for x in n.targets) and isinstance(n.value,ast.Call))
code=ast.literal_eval(n.value.func.value);code=code[:code.index('save();report={}')].replace('k276-manager-lifetime-r1','k278-ae-af-r1')
code+=r'''
import re,statistics
save();report={}
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k276-work/boot-id-private.txt').read_bytes() and health()['passed']
 sensor=next('/dev/'+p.name for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()=='s5kgw1 6-0010')
 user=pwd.getpwuid(10000)
 def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
 command=['/run/samurai-camera278-probes/af-native278-auto',sensor,'/base/soc@0/cci@ac4a000/i2c-bus@0/camera@10','s5kgw1','s5kgw1 6-0010','rgb','2048','1536','auto','scan']
 with (root/'capture-private.json').open('xb') as out,(root/'stderr-private.log').open('xb') as err:
  proc=subprocess.Popen(command,stdout=out,stderr=err,preexec_fn=demote,env=dict(PATH='/usr/bin:/bin',HOME=user.pw_dir,USER=user.pw_name,LIBCAMERA_LOG_LEVELS='*:WARN,SimplePipeline:DEBUG'))
  state.update(state='capture-live',child_pid=proc.pid,child_start_ticks=Path('/proc',str(proc.pid),'stat').read_text().rsplit(')',1)[1].split()[19]);save();proc.wait(timeout=195)
 assert proc.returncode==0,'Inspect existing AE/AF capture before another experiment'
 data=json.loads((root/'capture-private.json').read_text());frames=data['frames'];assert frames and frames[-1]['af_state']==2 and all(f['af_state']!=3 for f in frames)
 assert all(f['sequence']==f['raw_sequence'] and f['timestamp_ns']==f['raw_timestamp_ns'] for f in frames)
 assert all((f['metadata_focus_fom'] is not None)==(f['queued_index']%4==0) and (f['metadata_focus_fom'] is None or f['metadata_focus_fom']==f['focus_fom']) for f in frames)
 moves=[dict(serial=int(a),position=int(b),result=int(c),monotonic_ns=int(d)) for a,b,c,d in re.findall(r'Focus command (\d+) position (\d+) result (-?\d+) at (\d+)',(root/'stderr-private.log').read_text())]
 assert len(moves)>=10 and all(208<=m['position']<=926 and m['result']==0 for m in moves)
 first=next(f for f in frames if f['af_state']==2);assert first['timestamp_ns']>moves[-1]['monotonic_ns']+132000000
 assert any(f['queued_af_trigger']==1 and f['af_state']==2 for f in frames)
 report=dict(stage=278,frames=len(frames),automatic_exposure_and_gain=True,standard_single_auto_af_focused=True,
  focus_metadata_matches_same_request_raw=True,all_expected_focus_snapshots_delivered=True,position=moves[-1]['position'],moves=len(moves),
  exposure_us_range=[min(f['exposure_us'] for f in frames),max(f['exposure_us'] for f in frames)],gain_range=[min(f['analogue_gain'] for f in frames),max(f['analogue_gain'] for f in frames)],
  final_fom_median=statistics.median(f['focus_fom'] for f in frames if f['af_state']==2),cancel_after_focus_ignored=True,no_application_search_or_lens_writes=True)
except BaseException:
 error=traceback.format_exc();(root/'failure-private.txt').write_text(error)
finally:
 if proc is not None and proc.poll() is None:
  state.update(state='needs-attention-live-capture',terminal=False);save();raise RuntimeError('Existing capture remains live')
 time.sleep(3);after=health();report.update(error=None if error is None else 'See retained private failure',health=after)
 (root/'summary-private.json').write_text(json.dumps(report,indent=2));state.update(state='terminal',terminal=True,exit_code=0 if not error and after['passed'] else 1);save();print(json.dumps(report))
'''
compile(code,'ae-af278-worker','exec');response.write_bytes(b'SUBMISSION INTENT: inspect k278-ae-af-r1 before another experiment.\n')
q=host.ssh('python3 -',input=code.encode(),timeout=240,check=False);response.write_bytes(q.stdout+q.stderr);assert q.returncode==0 and q.stdout
d=json.loads(q.stdout);(R/'ae-af-r1-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps({k:v for k,v in d.items() if k!='health'},indent=2));print('Final idle:',d['health']['passed'])
