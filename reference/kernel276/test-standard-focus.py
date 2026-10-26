"""Use native libcamerasrc and standard V4L2 lens controls, without any raw I2C access."""
from pathlib import Path
import ast,json
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE;response=P/'standard-focus-r1-response-private.log';assert not response.exists()
t=ast.parse((R/'test-manager-lifetime.py').read_text());n=next(n for n in t.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='code' for x in n.targets) and isinstance(n.value,ast.Call))
base=ast.literal_eval(n.value.func.value);base=base[:base.index('save();report={}')].replace('k276-manager-lifetime-r1','k276-standard-focus-r1')
t=ast.parse((R.parent/'kernel274/probe-main-focus.py').read_text());n=next(n for n in t.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='code' for x in n.targets) and isinstance(n.value,ast.BinOp));tail=ast.literal_eval(n.value.right)
t=ast.parse(tail);n=next(n for n in t.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='worker' for x in n.targets));worker=ast.literal_eval(n.value)
code=base+'\nworker='+repr(worker)+'\n'+r'''
import statistics
user=pwd.getpwuid(10000);work=Path(user.pw_dir)/'.local/state/k276-standard-focus-r1';runs=[];report={};save()
def event(timeout=15):
 sel=selectors.DefaultSelector();sel.register(proc.stdout,selectors.EVENT_READ)
 try:
  assert sel.select(timeout),'No event from existing capture worker'
  line=proc.stdout.readline();assert line,'Existing capture worker exited';return json.loads(line)
 finally:sel.close()
def send(obj):proc.stdin.write(json.dumps(obj)+'\n');proc.stdin.flush()
def vaf():
 p=next(p for p in Path('/sys/class/regulator').glob('regulator.*') if (p/'name').read_text().strip()=='cam-main-vaf');return {k:(p/k).read_text().strip() for k in ['state','num_users']}
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k276-work/boot-id-private.txt').read_bytes()
 assert health()['passed'] and not work.exists();work.mkdir(mode=0o700);os.chown(work,user.pw_uid,user.pw_gid)
 lens=next('/dev/'+p.name for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()=='lc898219xi 6-0072')
 def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
 with (root/'capture-stderr-private.log').open('xb',buffering=0) as stderr:
  proc=subprocess.Popen(['python3','-u','-c',worker,str(work)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=stderr,text=True,bufsize=1,preexec_fn=demote,env=dict(PATH='/usr/sbin:/usr/bin:/sbin:/bin',HOME=user.pw_dir,USER=user.pw_name,GST_DEBUG_NO_COLOR='1'))
  state.update(state='capture-warmup',child_pid=proc.pid,child_start_ticks=Path('/proc',str(proc.pid),'stat').read_text().rsplit(')',1)[1].split()[19]);save();assert event(20)['event']=='ready'
  active=vaf();assert active==dict(state='enabled',num_users='1')
  assert Path('/sys/bus/i2c/devices/6-0072/power/runtime_status').read_text().strip()=='active'
  fds=[]
  for p in Path('/proc',str(proc.pid),'fd').iterdir():
   try:
    if os.readlink(p)==lens:fds.append(p.name)
   except OSError:pass
  assert len(fds)==1,'Actual capture process must hold the native lens descriptor'
  for index,position in enumerate([208,304,880,208]):
   state.update(state='standard-lens-control',index=index,position=position);save()
   q=subprocess.run(['v4l2-ctl','-d',lens,'--set-ctrl=focus_absolute='+str(position),'--get-ctrl=focus_absolute'],capture_output=True,text=True,timeout=10)
   (root/('control-'+str(index)+'-private.log')).write_text(q.stdout+q.stderr);assert q.returncode==0 and 'focus_absolute: '+str(position) in q.stdout
   time.sleep(.2);assert vaf()==active;send(dict(op='sample',index=index,position=position));row=event(15);assert row['event']=='phase' and row['position']==position;row['standard_control_exit']=q.returncode;row['cached_control_value']=position;runs.append(row);state['runs']=runs;save()
  send(dict(op='stop'));assert event(10)['event']=='stopped';proc.wait(timeout=10)
  report=dict(stage=276,standard_v4l2_focus_control=True,native_libcamerasrc=True,raw_i2c_transfers_used=False,capture_held_native_lens_fd=True,vaf_one_consumer_while_streaming=True,positions=[r['position'] for r in runs],all_four_phases_received=len(runs)==4)
except BaseException:
 error=traceback.format_exc();(root/'failure-private.txt').write_text(error)
finally:
 if proc is not None and proc.poll() is None:
  try:send(dict(op='stop'));proc.wait(timeout=10)
  except BaseException:state.update(state='needs-attention-live-capture',terminal=False);save();raise
 time.sleep(3);after=health()
 private=dict(report,runs=runs,error=error,exit=None if proc is None else proc.returncode,health=after);(root/'summary-private.json').write_text(json.dumps(private,indent=2)+'\n')
 public=[]
 for row in runs:
  public.append(dict(index=row['index'],position=row['position'],cached_control_value=row['cached_control_value'],samples=len(row['metrics']),median={k:statistics.median(m[k] for m in row['metrics']) for k in row['metrics'][0] if k!='pts'},jpeg={k:v for k,v in row['jpeg'].items() if k!='path'},jpeg_and_statistics_not_same_request=True))
 report.update(runs=public,error=None if error is None else 'See private failure log',exit=private['exit'],health=after,hardware_position_feedback_not_available=True,automatic_exposure_not_locked=True,autofocus_algorithm_not_implemented=True)
 state.update(state='terminal',terminal=True,exit_code=0 if not error and len(runs)==4 and after['passed'] else 1);save();print(json.dumps(report))
'''
compile(code,'standard-focus276-worker','exec');response.write_bytes(b'SUBMISSION INTENT: inspect k276-standard-focus-r1 if response is lost.\n')
q=host.ssh('python3 -',input=code.encode(),timeout=105,check=False);response.write_bytes(q.stdout+q.stderr);assert q.returncode==0 and q.stdout
d=json.loads(q.stdout);(R/'standard-focus-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps({k:v for k,v in d.items() if k not in ['runs','health']},indent=2));print('Final idle health:',d['health']['passed'])
