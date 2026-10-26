"""Compare real RAW contrast at standard lens positions with fixed exposure/gain."""
from pathlib import Path
import ast,hashlib,json,shlex
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE
proof=json.loads((R/'focus-probe-build-validation.json').read_text());binary=P/'focus-raw277'
assert hashlib.sha256(binary.read_bytes()).hexdigest()==proof['binary_sha256']
response=P/'raw-focus-r1-response-private.log';assert not response.exists()
remote='/run/samurai-camera277-probes/focus-raw277'
upload="from pathlib import Path;import sys,hashlib;p=Path(%r);assert not p.exists();p.parent.mkdir(mode=0o755,exist_ok=True);b=sys.stdin.buffer.read();assert hashlib.sha256(b).hexdigest()==%r;p.write_bytes(b);p.chmod(0o755)"%(remote,proof['binary_sha256'])
host.ssh('python3 -c '+shlex.quote(upload),input=binary.read_bytes(),timeout=15)
t=ast.parse((R.parent/'kernel276/test-manager-lifetime.py').read_text());n=next(n for n in t.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='code' for x in n.targets) and isinstance(n.value,ast.Call))
code=ast.literal_eval(n.value.func.value);code=code[:code.index('save();report={}')].replace('k276-manager-lifetime-r1','k277-raw-focus-r1')
code+='\nBINARY_SHA='+repr(proof['binary_sha256'])+'\n'+r'''
import statistics
save();runs=[];public=[];report={}
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k276-work/boot-id-private.txt').read_bytes()
 assert health()['passed']
 assert hashlib.sha256(Path('/run/samurai-camera277-probes/focus-raw277').read_bytes()).hexdigest()==BINARY_SHA
 sensor=next('/dev/'+p.name for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()=='s5kgw1 6-0010')
 lens=next('/dev/'+p.name for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()=='lc898219xi 6-0072')
 user=pwd.getpwuid(10000)
 def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
 for index,position in enumerate([208,304,880,208]):
  assert health()['passed']
  state.update(state='set-standard-focus',phase=index,position=position);save()
  q=subprocess.run(['v4l2-ctl','-d',lens,'--set-ctrl=focus_absolute='+str(position),'--get-ctrl=focus_absolute'],capture_output=True,text=True,timeout=10)
  (root/('control-'+str(index)+'-private.log')).write_text(q.stdout+q.stderr)
  assert q.returncode==0 and 'focus_absolute: '+str(position) in q.stdout
  command=['/run/samurai-camera277-probes/focus-raw277',sensor,'/base/soc@0/cci@ac4a000/i2c-bus@0/camera@10','s5kgw1','s5kgw1 6-0010','rgb','2048','1536','manual']
  with (root/('capture-'+str(index)+'-private.json')).open('xb') as out,(root/('capture-'+str(index)+'-stderr-private.log')).open('xb') as err:
   proc=subprocess.Popen(command,stdout=out,stderr=err,preexec_fn=demote,env=dict(PATH='/usr/bin:/bin',HOME=user.pw_dir,USER=user.pw_name))
   state.update(state='capture-live',child_pid=proc.pid,child_start_ticks=Path('/proc',str(proc.pid),'stat').read_text().rsplit(')',1)[1].split()[19]);save()
   proc.wait(timeout=110)
  assert proc.returncode==0,'Native capture failed; inspect retained output'
  data=json.loads((root/('capture-'+str(index)+'-private.json')).read_text());frames=data['frames'];assert len(frames)==24
  accepted=frames[12:];assert all(abs(f['exposure_us']-32000)<=40 and abs(f['analogue_gain']-1)<.03 for f in accepted)
  assert all(f['sequence']==f['raw_sequence'] and f['timestamp_ns']==f['raw_timestamp_ns'] for f in frames)
  row=dict(index=index,position=position,frames=24,settled_samples=len(accepted),exposure_us=[min(f['exposure_us'] for f in accepted),max(f['exposure_us'] for f in accepted)],
   analogue_gain=[min(f['analogue_gain'] for f in accepted),max(f['analogue_gain'] for f in accepted)],
   focus_fom_median=statistics.median(f['focus_fom'] for f in accepted),focus_fom_range=[min(f['focus_fom'] for f in accepted),max(f['focus_fom'] for f in accepted)],
   measurement_us_median=statistics.median(f['measurement_us'] for f in accepted),same_request_raw_rgb_verified=True)
  public.append(row);runs.append(data);state.update(state='capture-terminal',child_exit=proc.returncode,completed_phases=len(public));save();time.sleep(2)
  assert health()['passed']
except BaseException:
 error=traceback.format_exc();(root/'failure-private.txt').write_text(error)
finally:
 if proc is not None and proc.poll() is None:
  state.update(state='needs-attention-live-capture',terminal=False);save();raise RuntimeError('Capture still live; inspect same process before further tests')
 time.sleep(3);after=health()
 (root/'summary-private.json').write_text(json.dumps(dict(stage=277,runs=runs,summary=public,error=error,health=after),indent=2))
 report=dict(stage=277,runs=public,error=None if error is None else 'See retained private failure',health=after,
  candidate_helper_only=True,system_libcamera_still_r22=True,focus_fom_metadata_not_deployed=True,
  native_same_request_raw_rgb=True,raw_i2c_transfers_used=False,fixed_exposure_and_gain=True,autofocus_algorithm_not_implemented=True)
 state.update(state='terminal',terminal=True,exit_code=0 if not error and len(public)==4 and after['passed'] else 1);save();print(json.dumps(report))
'''
compile(code,'raw-focus277-worker','exec')
response.write_bytes(b'SUBMISSION INTENT: inspect k277-raw-focus-r1 if response is lost.\n')
q=host.ssh('python3 -',input=code.encode(),timeout=480,check=False);response.write_bytes(q.stdout+q.stderr)
assert q.returncode==0 and q.stdout
d=json.loads(q.stdout);(R/'raw-focus-r1-validation.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps({k:v for k,v in d.items() if k!='health'},indent=2));print('Final camera idle:',d['health']['passed'])
