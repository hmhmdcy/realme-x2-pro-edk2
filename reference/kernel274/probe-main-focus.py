"""Bounded OEM-derived lens movement with native user capture; not a product AF implementation."""
from pathlib import Path
import ast,json
import host
R=Path(__file__).resolve().parent
assert json.loads((R/'actuator-command-crosscheck-validation.json').read_text())['independent_xml_and_direct_decoder_agree']
assert json.loads((R/'actuator-read-r1-validation.json').read_text())['read_succeeded']
response=host.PRIVATE/'focus-position-r1-response-private.log';assert not response.exists()
tree=ast.parse((R/'read-main-actuator.py').read_text());n=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='code' for x in n.targets))
base=ast.literal_eval(n.value);base=base[:base.index('before=faults();proc=None;')].replace('k274-actuator-read-r1','k274-focus-position-r1')
code=base+r'''
import selectors,statistics,sys
def write_enable(fd):
 data=(ctypes.c_uint8*2)(0xe0,1);msgs=(Msg*1)(Msg(0x72,0,2,data));t=Transfer(msgs,1)
 assert fcntl.ioctl(fd,0x0707,t)==1;time.sleep(.001)
def write_position(fd,value):
 assert 208<=value<=880
 data=(ctypes.c_uint8*3)(0x84,value>>8,value&255);msgs=(Msg*1)(Msg(0x72,0,3,data));t=Transfer(msgs,1)
 assert fcntl.ioctl(fd,0x0707,t)==1;time.sleep(.001)
worker=r"""
from pathlib import Path
import hashlib,json,sys,time,gi
gi.require_version('Gst','1.0')
from gi.repository import Gst
Gst.init(None);out=Path(sys.argv[1]);width,height=1280,960
pipeline=Gst.parse_launch('libcamerasrc camera-name="/base/soc@0/cci@ac4a000/i2c-bus@0/camera@10" ! video/x-raw,format=RGBx,width=1280,height=960 ! tee name=t t. ! queue leaky=downstream max-size-buffers=1 ! appsink name=raw sync=false max-buffers=1 drop=true t. ! queue leaky=downstream max-size-buffers=1 ! videoconvert ! jpegenc quality=95 ! appsink name=jpeg sync=false max-buffers=1 drop=true')
raw=pipeline.get_by_name('raw');jpeg=pipeline.get_by_name('jpeg')
def sample(sink):
 s=sink.emit('try-pull-sample',4*Gst.SECOND)
 if s is None:raise RuntimeError('No capture sample')
 b=s.get_buffer();ok,m=b.map(Gst.MapFlags.READ);assert ok
 try:data=bytes(m.data)
 finally:b.unmap(m)
 return data,int(b.pts)
def emit(obj):print(json.dumps(obj),flush=True)
try:
 assert pipeline.set_state(Gst.State.PLAYING)!=Gst.StateChangeReturn.FAILURE
 for _ in range(120):sample(raw)
 emit(dict(event='ready',warmup_frames=120))
 for command in sys.stdin:
  cmd=json.loads(command)
  if cmd['op']=='stop':break
  index,position=cmd['index'],cmd['position']
  for _ in range(8):sample(raw)
  metrics=[]
  for _ in range(6):
   data,pts=sample(raw);assert len(data)==width*height*4
   total=squares=edges=lap2=clipped=count=0
   for y in range(240,720,2):
    for x in range(320,960,2):
     i=(y*width+x)*4+1;g=data[i];dx=g-data[i+8];dy=g-data[i+width*8]
     lap=4*g-data[i-8]-data[i+8]-data[i-width*8]-data[i+width*8]
     total+=g;squares+=g*g;edges+=abs(dx)+abs(dy);lap2+=lap*lap;clipped+=g>=250;count+=1
   mean=total/count;variance=squares/count-mean*mean
   metrics.append(dict(pts=pts,green_mean=mean,green_stddev=max(0,variance)**.5,gradient=edges/(2*count),normalized_gradient=edges/max(1,2*total),laplacian_energy=lap2/count,normalized_laplacian=(lap2/count)/max(1,mean*mean),clipped_fraction=clipped/count))
  image,jpeg_pts=sample(jpeg);target=out/('focus-'+str(index)+'-'+str(position)+'-private.jpg');target.write_bytes(image)
  emit(dict(event='phase',index=index,position=position,metrics=metrics,jpeg=dict(bytes=len(image),sha256=hashlib.sha256(image).hexdigest(),path=str(target),pts=jpeg_pts),jpeg_and_statistics_not_same_request=True))
finally:
 pipeline.set_state(Gst.State.NULL)
emit(dict(event='stopped'))
"""
before=faults();proc=None;save();error=None;runs=[];enabled=False;parked=False
u=pwd.getpwuid(10000);work=Path(u.pw_dir)/'.local/state/k274-focus-position-r1'
def event(timeout=15):
 sel=selectors.DefaultSelector();sel.register(proc.stdout,selectors.EVENT_READ)
 try:
  assert sel.select(timeout),'Capture worker event timeout; inspect the existing process'
  line=proc.stdout.readline();assert line,'Capture worker exited; inspect stderr'
  return json.loads(line)
 finally:sel.close()
def send(obj):proc.stdin.write(json.dumps(obj)+'\n');proc.stdin.flush()
def move(fd,value):
 current=int(read_register(fd,0x84,2),16);assert 0<=current<=1023
 # Only the initial transition may start below the chosen optical test interval.
 if current<208:write_position(fd,208);current=208
 while current!=value:
  current+=max(-64,min(64,value-current));write_position(fd,current)
 assert int(read_register(fd,0x84,2),16)==value
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k273-work/boot-id-private.txt').read_bytes()
 assert health()['passed'] and not work.exists()
 assert not Path('/sys/bus/i2c/devices/6-0072').exists()
 work.mkdir(mode=0o700);os.chown(work,u.pw_uid,u.pw_gid)
 def demote():resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.initgroups(u.pw_name,u.pw_gid);os.setgid(u.pw_gid);os.setuid(u.pw_uid)
 stderr=(root/'capture-stderr-private.log').open('xb',buffering=0)
 proc=subprocess.Popen(['python3','-u','-c',worker,str(work)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=stderr,text=True,bufsize=1,preexec_fn=demote,env=dict(PATH='/usr/sbin:/usr/bin:/sbin:/bin',HOME=u.pw_dir,USER=u.pw_name,GST_DEBUG_NO_COLOR='1'))
 state.update(state='warming',child_pid=proc.pid,child_start_ticks=Path('/proc',str(proc.pid),'stat').read_text().rsplit(')',1)[1].split()[19]);save()
 assert event(18)['event']=='ready'
 active=rails();assert active['cam-main-vaf']['state']=='enabled' and active['cam-main-vaf']['microvolts']=='2800000'
 with open('/dev/i2c-6','rb',buffering=0) as fd:
  state.update(state='enable-oem-actuator');save();write_enable(fd)
  enable_value=read_register(fd,0xe0,1);assert enable_value=='01','OEM enable readback mismatch'
  enabled=True
  for index,position in enumerate([208,304,400,496,592,688,784,880,208]):
   state.update(state='position',index=index,position=position);save();move(fd,position);time.sleep(.15)
   readback=read_register(fd,0x84,2);send(dict(op='sample',index=index,position=position));row=event(12)
   assert row['event']=='phase' and row['index']==index and row['position']==position
   row['position_readback']=readback;runs.append(row);state['runs']=runs;save()
  move(fd,208);parked=True
except BaseException:
 error=traceback.format_exc();(root/'failure-private.txt').write_text(error)
finally:
 if proc is not None and proc.poll() is None:
  if enabled and not parked:
   try:
    with open('/dev/i2c-6','rb',buffering=0) as fd:move(fd,208);parked=True
   except BaseException:(root/'park-failure-private.txt').write_text(traceback.format_exc())
  state.update(state='stopping');save()
  try:send(dict(op='stop'));stopped=event(8);assert stopped['event']=='stopped';proc.wait(timeout=8)
  except BaseException:
   if proc.poll() is None:state.update(state='needs-attention-live-capture',terminal=False);save();raise
 time.sleep(3);after=health()
 private=dict(stage=274,runs=runs,health=after,enabled=enabled,parked=parked,error=error,capture_exit=None if proc is None else proc.returncode)
 (root/'summary-private.json').write_text(json.dumps(private,indent=2)+'\n');(root/'dmesg-after-private.log').write_bytes(subprocess.check_output(['dmesg']))
 public=[]
 for row in runs:
  metrics=row['metrics'];public.append(dict(index=row['index'],position=row['position'],position_readback=row['position_readback'],samples=len(metrics),median={k:statistics.median(m[k] for m in metrics) for k in metrics[0] if k!='pts'},jpeg={k:v for k,v in row['jpeg'].items() if k!='path'},jpeg_and_statistics_not_same_request=True))
 report=dict(stage=274,runs=public,enabled_readback_verified=enabled,parked_at_oem_initial_code=parked,capture_exit=private['capture_exit'],health=after,error=None if error is None else 'See private failure log',
  diagnostic_oem_i2c_not_standard_lens_driver=True,automatic_exposure_not_locked=True,no_otp_or_calibration_write=True,no_spectra_processing=True)
 state.update(state='terminal',terminal=True,exit_code=0 if len(runs)==9 and after['passed'] and not error else 1);save();print(json.dumps(report))
'''
compile(code,'focus-position-worker274.py','exec')
response.write_bytes(b'SUBMISSION INTENT: inspect /var/lib/samurai/k274-focus-position-r1 if response is lost.\n')
q=host.ssh('python3 -',input=code.encode(),timeout=120,check=False);response.write_bytes(q.stdout+q.stderr)
assert q.returncode==0 and q.stdout,'Inspect the submitted focus worker; do not resubmit'
d=json.loads(q.stdout);(R/'focus-position-r1-validation.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps({k:v for k,v in d.items() if k not in ['runs','health']},indent=2));print(json.dumps([dict(position=r['position'],mean=r['median']['green_mean'],gradient=r['median']['normalized_gradient'],laplacian=r['median']['normalized_laplacian']) for r in d['runs']],indent=2));print('idle health passed:',d['health']['passed'])
