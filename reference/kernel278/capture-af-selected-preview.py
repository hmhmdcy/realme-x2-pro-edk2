"""Review the selected lens position in a subsequent native preview, without refocusing."""
from pathlib import Path
import ast,json
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE
af=json.loads((R/'ae-af-r1-validation.json').read_text());assert af['error'] is None and af['standard_single_auto_af_focused']
assert json.loads((R/'four-camera-regression-validation.json').read_text())['passed']
response=P/'af-selected-preview-response-private.log';assert not response.exists()
t=ast.parse((R.parent/'kernel274/probe-main-focus.py').read_text());n=next(n for n in t.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='code' for x in n.targets) and isinstance(n.value,ast.BinOp));tail=ast.literal_eval(n.value.right)
t=ast.parse(tail);n=next(n for n in t.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='worker' for x in n.targets));worker=ast.literal_eval(n.value)
t=ast.parse((R.parent/'kernel276/test-manager-lifetime.py').read_text());n=next(n for n in t.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='code' for x in n.targets) and isinstance(n.value,ast.Call))
code=ast.literal_eval(n.value.func.value);code=code[:code.index('save();report={}')].replace('k276-manager-lifetime-r1','k278-af-selected-preview')
code+='\nworker='+repr(worker)+'\nEXPECTED_POSITION='+repr(af['position'])+'\n'+r'''
import re,statistics
save();row=None
def event(timeout):
 sel=selectors.DefaultSelector();sel.register(proc.stdout,selectors.EVENT_READ)
 try:assert sel.select(timeout);line=proc.stdout.readline();assert line;return json.loads(line)
 finally:sel.close()
def send(value):proc.stdin.write(json.dumps(value)+'\n');proc.stdin.flush()
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k276-work/boot-id-private.txt').read_bytes() and health()['passed']
 lens=next('/dev/'+p.name for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()=='lc898219xi 6-0072')
 def position():
  q=subprocess.run(['v4l2-ctl','-d',lens,'--get-ctrl=focus_absolute'],capture_output=True,text=True,timeout=10);assert q.returncode==0;return int(re.search(r'focus_absolute: (\d+)',q.stdout).group(1))
 assert position()==EXPECTED_POSITION;time.sleep(.3)
 user=pwd.getpwuid(10000);work=Path(user.pw_dir)/'.local/state/k278-af-selected-preview';work.mkdir(mode=0o700);os.chown(work,user.pw_uid,user.pw_gid)
 def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
 with (root/'stderr-private.log').open('xb',buffering=0) as err:
  proc=subprocess.Popen(['python3','-u','-c',worker,str(work)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,text=True,bufsize=1,preexec_fn=demote,
   env=dict(PATH='/usr/bin:/bin',HOME=user.pw_dir,USER=user.pw_name,GST_DEBUG_NO_COLOR='1',LIBCAMERA_LOG_LEVELS='*:WARN,SimplePipeline:DEBUG'))
  state.update(state='capture-live',child_pid=proc.pid,child_start_ticks=Path('/proc',str(proc.pid),'stat').read_text().rsplit(')',1)[1].split()[19]);save()
  assert event(25)['event']=='ready';send(dict(op='sample',index=0,position=EXPECTED_POSITION));row=event(20);assert row['event']=='phase'
  send(dict(op='stop'));assert event(10)['event']=='stopped';proc.wait(timeout=10);assert proc.returncode==0
 assert 'Focus command ' not in (root/'stderr-private.log').read_text();assert position()==EXPECTED_POSITION
except BaseException:
 error=traceback.format_exc();(root/'failure-private.txt').write_text(error)
finally:
 if proc is not None and proc.poll() is None:
  try:send(dict(op='stop'));proc.wait(timeout=10)
  except BaseException:state.update(state='needs-attention-live-capture',terminal=False);save();raise
 time.sleep(3);after=health()
 (root/'summary-private.json').write_text(json.dumps(dict(stage=278,phase=row,error=error,health=after),indent=2))
 report=dict(stage=278,error=None if error is None else 'See retained private failure',cached_position=EXPECTED_POSITION,subsequent_native_libcamerasrc_preview=True,
  af_request_and_jpeg_are_different_sessions=True,application_lens_writes=False,no_new_af_command_in_preview=True,health=after,
  jpeg=None if row is None else {k:v for k,v in row['jpeg'].items() if k!='path'},sample_count=0 if row is None else len(row['metrics']))
 state.update(state='terminal',terminal=True,exit_code=0 if not error and after['passed'] else 1);save();print(json.dumps(report))
'''
compile(code,'af-selected-preview-worker','exec');response.write_bytes(b'SUBMISSION INTENT: inspect k278-af-selected-preview before another capture.\n')
q=host.ssh('python3 -',input=code.encode(),timeout=90,check=False);response.write_bytes(q.stdout+q.stderr);assert q.returncode==0 and q.stdout
d=json.loads(q.stdout);(R/'af-selected-preview-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps({k:v for k,v in d.items() if k!='health'},indent=2));print('Final idle:',d['health']['passed'])
