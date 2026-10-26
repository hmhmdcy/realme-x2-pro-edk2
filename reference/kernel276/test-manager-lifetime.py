"""Verify a live CameraManager can retain all cameras while every lens/camera rail is idle."""
from pathlib import Path
import hashlib,json,shlex
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE;proof=json.loads((R/'manager-probe-build-validation.json').read_text());binary=P/'manager-hold276';assert hashlib.sha256(binary.read_bytes()).hexdigest()==proof['binary_sha256']
response=P/'manager-lifetime-r1-response-private.log';assert not response.exists();remote='/run/samurai-camera276-probes/manager-hold276'
code="from pathlib import Path;import sys,hashlib,os;p=Path(%r);assert not p.exists();p.parent.mkdir(mode=0o755,exist_ok=True);b=sys.stdin.buffer.read();assert hashlib.sha256(b).hexdigest()==%r;p.write_bytes(b);p.chmod(0o755)"%(remote,proof['binary_sha256'])
host.ssh('python3 -c '+shlex.quote(code),input=binary.read_bytes(),timeout=15)
code=r'''
from pathlib import Path
import hashlib,json,os,pwd,selectors,subprocess,time,traceback
os.umask(0o077);root=Path('/var/lib/samurai/k276-manager-lifetime-r1');root.mkdir(mode=0o700);state=dict(state='preflight',terminal=False,pid=os.getpid());proc=None;error=None
def save():(root/'state-private.json').write_text(json.dumps(state,indent=2)+'\n')
def counts():
 b=subprocess.check_output(['dmesg']);return {k:b.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',fatal=b'fatal error received',cci_queue_timeout=b'queue 0 timeout').items()}
before=counts()
def health():
 runtime={}
 for bus,names in [('i2c',['6-0010','7-0010','8-002d','9-0010','6-0072']),('platform',['ac4a000.cci','ac4b000.cci','acb3000.camss'])]:
  for n in names:runtime[n]=Path('/sys/bus',bus,'devices',n,'power/runtime_status').read_text().strip()
 rails={}
 for p in Path('/sys/class/regulator').glob('regulator.*'):
  name=(p/'name').read_text().strip()
  if name.startswith(('cam-main-','cam-front-','cam-rear-','cam-tele-')):rails[name]={k:(p/k).read_text().strip() for k in ['state','num_users']}
 lines=Path('/sys/kernel/debug/clk/clk_summary').read_text().splitlines();clocks={name:int(next(l.split()[1] for l in lines if l.split() and l.split()[0]==name)) for name in ['cam_cc_mclk0_clk','cam_cc_mclk1_clk','cam_cc_mclk2_clk','cam_cc_mclk3_clk','cam_cc_cci_0_clk','cam_cc_cci_1_clk']}
 faults={k:v-before[k] for k,v in counts().items()};taint=int(Path('/proc/sys/kernel/tainted').read_text());passed=all(v=='suspended' for v in runtime.values()) and len(rails)==9 and all(v['state']=='disabled' and v['num_users']=='0' for v in rails.values()) and not any(clocks.values()) and not any(faults.values()) and taint==0
 return dict(runtime=runtime,rails=rails,clocks=clocks,fault_delta=faults,taint=taint,passed=passed)
save();report={}
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k276-work/boot-id-private.txt').read_bytes()
 assert health()['passed']
 assert hashlib.sha256(Path('/run/samurai-camera276-probes/manager-hold276').read_bytes()).hexdigest()==EXPECTED
 user=pwd.getpwuid(10000)
 def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
 with (root/'stderr-private.log').open('xb',buffering=0) as stderr:
  proc=subprocess.Popen(['/run/samurai-camera276-probes/manager-hold276'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=stderr,text=True,bufsize=1,preexec_fn=demote,env=dict(PATH='/usr/bin:/bin',HOME=user.pw_dir,USER=user.pw_name))
  state.update(state='manager-live',child_pid=proc.pid,child_start_ticks=Path('/proc',str(proc.pid),'stat').read_text().rsplit(')',1)[1].split()[19]);save()
  selector=selectors.DefaultSelector();selector.register(proc.stdout,selectors.EVENT_READ);assert selector.select(15);ready=json.loads(proc.stdout.readline());selector.close();assert ready==dict(event='ready',cameras=4)
  time.sleep(3);assert proc.poll() is None
  lens=next('/dev/'+p.name for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()=='lc898219xi 6-0072')
  held=[]
  for p in Path('/proc',str(proc.pid),'fd').iterdir():
   try:
    if os.readlink(p)==lens:held.append(p.name)
   except OSError:pass
  live=health();stderr_text=(root/'stderr-private.log').read_text();assert not held and live['passed'] and 'Lens initialisation failed' not in stderr_text and 'lc898219xi' not in ''.join(l for l in stderr_text.splitlines() if 'ERROR' in l)
  report=dict(stage=276,four_cameras_enumerated=True,manager_alive_during_idle_check=True,lens_fd_not_retained_by_manager=True,no_lens_initialization_error=True,live_idle_health=live)
except BaseException:
 error=traceback.format_exc();(root/'failure-private.txt').write_text(error)
finally:
 if proc is not None and proc.poll() is None:
  proc.stdin.write('stop\n');proc.stdin.flush();proc.wait(timeout=10)
 time.sleep(2);report.update(exit=None if proc is None else proc.returncode,error=error,final_health=health())
 state.update(state='terminal',terminal=True,exit_code=0 if not error and report['final_health']['passed'] else 1);save();(root/'summary-private.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''.replace('EXPECTED',repr(proof['binary_sha256']))
response.write_bytes(b'SUBMISSION INTENT: inspect k276-manager-lifetime-r1 if response is lost.\n')
q=host.ssh('python3 -',input=code.encode(),timeout=45,check=False);response.write_bytes(q.stdout+q.stderr);assert q.returncode==0 and q.stdout
d=json.loads(q.stdout);(R/'manager-lifetime-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
