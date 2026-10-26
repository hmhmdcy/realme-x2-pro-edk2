"""Read the OEM LC candidate's ordinary registers while standard RAW capture owns power."""
from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
proof=json.loads((R/'actuator-contract-validation.json').read_text())
assert proof['variants'][0]['address7']==0x72 and proof['no_actuator_operation']
response=host.PRIVATE/'actuator-read-r1-response-private.log'
assert not response.exists(),'Inspect the existing submitted worker instead of resubmitting'
code=r'''
from pathlib import Path
import ctypes,fcntl,hashlib,json,os,pwd,re,resource,signal,subprocess,time,traceback
os.umask(0o077);root=Path('/var/lib/samurai/k274-actuator-read-r1');root.mkdir(mode=0o700)
state=dict(stage=274,state='preflight',terminal=False,pid=os.getpid())
def save():(root/'state-private.json').write_text(json.dumps(state,indent=2)+'\n')
def faults():
 b=subprocess.check_output(['dmesg'])
 return {k:b.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',fatal=b'fatal error received',modem=b'crash detected in modem').items()}
def rails():
 out={}
 for p in Path('/sys/class/regulator').glob('regulator.*'):
  n=(p/'name').read_text().strip()
  if n.startswith(('cam-front-','cam-rear-','cam-tele-','cam-main-')):out[n]={k:(p/k).read_text().strip() for k in ['state','num_users','microvolts']}
 return out
def health():
 runtime={}
 for bus,names in [('i2c',['6-0010','7-0010','8-002d','9-0010']),('platform',['ac4a000.cci','ac4b000.cci','acb3000.camss'])]:
  for n in names:runtime[n]=Path('/sys/bus',bus,'devices',n,'power/runtime_status').read_text().strip()
 lines=Path('/sys/kernel/debug/clk/clk_summary').read_text().splitlines()
 clocks={n:int(next(l.split()[1] for l in lines if l.split() and l.split()[0]==n)) for n in ['cam_cc_mclk0_clk','cam_cc_mclk1_clk','cam_cc_mclk2_clk','cam_cc_mclk3_clk']}
 r=rails();f={k:v-before[k] for k,v in faults().items()};taint=int(Path('/proc/sys/kernel/tainted').read_text())
 return dict(runtime=runtime,rails=r,mclk=clocks,fault_delta=f,taint=taint,passed=all(v=='suspended' for v in runtime.values()) and len(r)==9 and all(v['state']=='disabled' and v['num_users']=='0' for v in r.values()) and not any(clocks.values()) and not any(f.values()) and taint==0)
class Msg(ctypes.Structure):_fields_=[('addr',ctypes.c_uint16),('flags',ctypes.c_uint16),('len',ctypes.c_uint16),('buf',ctypes.POINTER(ctypes.c_uint8))]
class Transfer(ctypes.Structure):_fields_=[('msgs',ctypes.POINTER(Msg)),('nmsgs',ctypes.c_uint32)]
def read_register(fd,reg,length):
 assert reg in [0x84,0xe0] and length in [1,2]
 pointer=(ctypes.c_uint8*1)(reg);data=(ctypes.c_uint8*length)()
 msgs=(Msg*2)(Msg(0x72,0,1,pointer),Msg(0x72,1,length,data));transfer=Transfer(msgs,2)
 assert fcntl.ioctl(fd,0x0707,transfer)==2
 return bytes(data).hex()
before=faults();proc=None;save();error=None;reads=[]
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k273-work/boot-id-private.txt').read_bytes()
 assert health()['passed']
 ko=Path('/usr/lib/modules')/os.uname().release/'kernel/drivers/media/i2c/s5kgw1.ko'
 assert hashlib.sha256(ko.read_bytes()).hexdigest()=='0c907b122065b8657dc9f9e68ff17784c5419ed1994fe9f1ced5ccfa60c90ade'
 assert Path('/sys/bus/i2c/devices/i2c-6/of_node').resolve().as_posix().endswith('/soc@0/cci@ac4a000/i2c-bus@0')
 assert not Path('/sys/bus/i2c/devices/6-0072').exists()
 for p in Path('/proc').glob('[0-9]*'):
  try:name=(p/'comm').read_text().strip()
  except OSError:continue
  assert name not in ['cam','snapshot','megapixels','gst-launch-1.0','main-worker-pro'],'Camera client active'
 u=pwd.getpwuid(10000)
 def demote():resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.initgroups(u.pw_name,u.pw_gid);os.setgid(u.pw_gid);os.setuid(u.pw_uid)
 with (root/'cam-stdout-private.log').open('xb',buffering=0) as stdout,(root/'cam-stderr-private.log').open('xb',buffering=0) as stderr:
  proc=subprocess.Popen(['cam','-c','/base/soc@0/cci@ac4a000/i2c-bus@0/camera@10','--capture=300','--stream','role=raw'],env=dict(PATH='/usr/sbin:/usr/bin:/sbin:/bin',HOME=u.pw_dir,USER=u.pw_name),preexec_fn=demote,stdout=stdout,stderr=stderr)
  state.update(state='streaming',child_pid=proc.pid,child_start_ticks=Path('/proc',str(proc.pid),'stat').read_text().rsplit(')',1)[1].split()[19]);save()
  deadline=time.monotonic()+18
  while time.monotonic()<deadline:
   assert proc.poll() is None,'Capture exited before read'
   if len(re.findall(rb'seq:\s*(\d+)',(root/'cam-stdout-private.log').read_bytes()))>=5:break
   time.sleep(.05)
  else:raise RuntimeError('No five RAW frames before read deadline')
  active=rails();assert active['cam-main-vaf']['state']=='enabled' and active['cam-main-vaf']['microvolts']=='2800000'
  assert Path('/sys/bus/i2c/devices/6-0010/power/runtime_status').read_text().strip()=='active'
  state.update(state='reading-ordinary-registers');save()
  with open('/dev/i2c-6','rb',buffering=0) as fd:
   for i in range(2):
    reads.append(dict(sample=i,position_register_84=read_register(fd,0x84,2),enable_register_e0=read_register(fd,0xe0,1)))
    time.sleep(.05)
  state.update(reads=reads,active_vaf=active['cam-main-vaf']);save()
except BaseException:
 error=traceback.format_exc();(root/'failure-private.txt').write_text(error)
finally:
 if proc is not None and proc.poll() is None:
  state.update(state='stopping-once');save();proc.send_signal(signal.SIGINT)
  try:proc.wait(timeout=10)
  except subprocess.TimeoutExpired:
   state.update(state='needs-attention-live-capture',terminal=False);save();raise
 time.sleep(3)
 after=health();seq=re.findall(rb'seq:\s*(\d+)',(root/'cam-stdout-private.log').read_bytes()) if proc else []
 report=dict(stage=274,read_succeeded=len(reads)==2,error=None if error is None else 'See private failure log',reads=reads,capture_exit=None if proc is None else proc.returncode,raw_frames=len(seq),health=after,
  no_register_data_written=True,no_lens_motion_requested=True,only_pointer_writes_84_e0=True,chip_identity_not_proven=True)
 (root/'summary.json').write_text(json.dumps(report,indent=2)+'\n');(root/'dmesg-after-private.log').write_bytes(subprocess.check_output(['dmesg']))
 state.update(state='terminal',terminal=True,exit_code=0 if report['read_succeeded'] and after['passed'] else 1);save();print(json.dumps(report))
'''
compile(code,'actuator-read-worker274.py','exec')
response.write_bytes(b'SUBMISSION INTENT: inspect /var/lib/samurai/k274-actuator-read-r1 if response is lost.\n')
q=host.ssh('python3 -',input=code.encode(),timeout=50,check=False);response.write_bytes(q.stdout+q.stderr)
assert q.returncode==0 and q.stdout,'Inspect the submitted worker before any further transfer'
d=json.loads(q.stdout);(R/'actuator-read-r1-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
