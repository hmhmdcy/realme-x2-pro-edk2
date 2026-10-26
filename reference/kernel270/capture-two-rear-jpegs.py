"""Use native libcamerasrc and CPU JPEG encoding for both observed rear camera IDs."""
from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import hashlib,json,os,pwd,re,subprocess,time,traceback
os.umask(0o077);root=Path('/var/lib/samurai/k270-two-rear-jpeg-r1');root.mkdir(mode=0o700)
u=pwd.getpwuid(10000);work=Path(u.pw_dir)/'.local/state/k270-two-rear-jpeg-r1';assert not work.exists();work.mkdir(mode=0o700);os.chown(work,u.pw_uid,u.pw_gid)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k270-work/boot-id-private.txt').read_bytes()
state=dict(state='preflight',terminal=False,pid=os.getpid(),runs=[])
def save():(root/'state-private.json').write_text(json.dumps(state,indent=2)+'\n')
def faults(b):return {k:b.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',fatal=b'fatal error received',modem=b'crash detected in modem').items()}
save();before=subprocess.check_output(['dmesg']);assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and not any(faults(before).values())
worker=r"""
from pathlib import Path
import hashlib,json,os,sys,time,traceback,gi
gi.require_version('Gst','1.0')
from gi.repository import Gst
Gst.init(None)
which,ident,out=sys.argv[1:];out=Path(out)
pipeline=Gst.parse_launch('libcamerasrc camera-name="'+ident+'" ! video/x-raw,format=RGBx ! videoconvert ! jpegenc quality=90 ! appsink name=photo sync=false max-buffers=1 drop=true')
sink=pipeline.get_by_name('photo');frames=[];image=None
try:
 assert pipeline.set_state(Gst.State.PLAYING)!=Gst.StateChangeReturn.FAILURE
 for i in range(36):
  sample=sink.emit('try-pull-sample',4*Gst.SECOND)
  if sample is None:
   bus=pipeline.get_bus();message=bus.timed_pop_filtered(0,Gst.MessageType.ERROR|Gst.MessageType.EOS)
   raise RuntimeError(str(message.parse_error()) if message and message.type==Gst.MessageType.ERROR else 'No JPEG sample')
  buffer=sample.get_buffer();caps=sample.get_caps().get_structure(0)
  ok,mapping=buffer.map(Gst.MapFlags.READ);assert ok
  try:image=bytes(mapping.data)
  finally:buffer.unmap(mapping)
  frames.append(dict(pts=int(buffer.pts),bytes=len(image)))
 assert image and len(image)>1024 and all(b['pts']>a['pts'] for a,b in zip(frames,frames[1:]))
 target=out/(which+'-private.jpg');target.write_bytes(image)
 report=dict(camera=which,frames=len(frames),pts=frames,width=caps.get_value('width'),height=caps.get_value('height'),jpeg_bytes=len(image),sha256=hashlib.sha256(image).hexdigest(),path=str(target))
 print(json.dumps(report))
finally:pipeline.set_state(Gst.State.NULL)
"""
(root/'jpeg-worker.py').write_text(worker)
def demote():os.initgroups(u.pw_name,u.pw_gid);os.setgid(u.pw_gid);os.setuid(u.pw_uid)
env=dict(PATH='/usr/sbin:/usr/bin:/sbin:/bin',HOME=u.pw_dir,USER=u.pw_name,GST_DEBUG_NO_COLOR='1')
try:
 for which,ident in [('wide','/base/soc@0/cci@ac4a000/i2c-bus@1/camera@10'),('tele','/base/soc@0/cci@ac4b000/i2c-bus@0/camera@2d')]:
  state['state']='capturing-'+which;save()
  # The worker itself is supplied on stdin so its private parent need not be traversable by the user.
  q=subprocess.run(['python3','-c',worker,which,ident,str(work)],env=env,preexec_fn=demote,capture_output=True,timeout=35)
  (root/(which+'-stdout-private.json')).write_bytes(q.stdout);(root/(which+'-stderr-private.log')).write_bytes(q.stderr)
  if q.returncode:state['runs'].append(dict(camera=which,exit=q.returncode,passed=False));break
  row=json.loads(q.stdout);time.sleep(1)
  after=subprocess.check_output(['dmesg']);row['fault_delta']={k:v-faults(before)[k] for k,v in faults(after).items()}
  row['runtime_after']={n:Path('/sys/bus/i2c/devices',n,'power/runtime_status').read_text().strip() for n in ['7-0010','8-002d','9-0010']}
  row['taint']=int(Path('/proc/sys/kernel/tainted').read_text());row['passed']=not any(row['fault_delta'].values()) and row['taint']==0 and all(v=='suspended' for v in row['runtime_after'].values())
  state['runs'].append(row);save()
  if not row['passed']:break
 report=dict(stage=270,runs=state['runs'],passed=len(state['runs'])==2 and all(r['passed'] for r in state['runs']),
  native_libcamerasrc=True,cpu_software_isp_and_cpu_jpeg=True,no_spectra_processing=True)
 (root/'summary-private.json').write_text(json.dumps(report,indent=2)+'\n');state.update(state='terminal',terminal=True,exit_code=0 if report['passed'] else 1);save();print(json.dumps(report))
except BaseException:
 (root/'failure-private.txt').write_text(traceback.format_exc());state.update(state='failed',terminal=True,exit_code=1);save();raise
'''
q=host.ssh('python3 -',input=code.encode(),timeout=90,check=False)
(host.PRIVATE/'two-rear-jpeg-response-private.log').write_bytes(q.stdout+q.stderr)
assert q.stdout,'Read the worker state before any further action'
d=json.loads(q.stdout)
for row in d['runs']:
 row.pop('path',None)
 if 'pts' in row:
  pts=row.pop('pts');row['first_pts']=pts[0]['pts'];row['last_pts']=pts[-1]['pts']
(R/'two-rear-jpeg-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
