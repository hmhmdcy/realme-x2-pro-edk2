"""Read current factory EEPROM maps while ordinary cam streams own power."""
from pathlib import Path
import ctypes,fcntl,hashlib,json,os,pwd,re,select,signal,subprocess,sys,time,traceback
os.umask(0o077)
root=Path(sys.argv[1]);marker=root/'state.json'
if marker.exists():raise RuntimeError('Inspect the existing read instead of replaying it')
state=dict(stage=326,pid=os.getpid(),terminal=False,phase='preflight')
def save(phase,**kw):state.update(phase=phase,**kw);marker.write_text(json.dumps(state,indent=2)+'\n')
def stop_requested(signum,frame):raise InterruptedError('Read stopped by signal')
signal.signal(signal.SIGINT,stop_requested);signal.signal(signal.SIGTERM,stop_requested)
def processes(name):
 result=[]
 for p in Path('/proc').glob('[0-9]*'):
  try:
   if (p/'comm').read_text().strip()==name and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z':result.append(p)
  except (FileNotFoundError,ProcessLookupError):pass
 return result
def services():
 result={}
 for name in ['pipewire','wireplumber']:
  ps=processes(name)
  if len(ps)!=1:raise RuntimeError('Expected one '+name)
  p=ps[0];result[name]=dict(pid=int(p.name),uid=p.stat().st_uid,argv=[v.decode() for v in (p/'cmdline').read_bytes().split(b'\0') if v],cwd=os.readlink(p/'cwd'),env=dict(v.decode().split('=',1) for v in (p/'environ').read_bytes().split(b'\0') if v))
 return result
def health():
 sensors={}
 for driver in ['s5kgw1','s5k3m5','imx319','imx471','lc898219xi']:
  devices=[p for p in (Path('/sys/bus/i2c/drivers')/driver).iterdir() if (p/'of_node').exists()]
  if len(devices)!=1:raise RuntimeError('Unexpected sensor/lens binding: '+driver)
  sensors[driver]=(devices[0]/'power/runtime_status').read_text().strip()
 return dict(sensors=sensors,platforms={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['acb3000.camss','ac4a000.cci','ac4b000.cci']},
  rails={(p/'name').read_text().strip():dict(state=(p/'state').read_text().strip(),users=int((p/'num_users').read_text())) for p in Path('/sys/class/regulator').glob('regulator.*') if (p/'name').read_text().startswith(('cam-main-','cam-front-','cam-rear-','cam-tele-'))},taint=int(Path('/proc/sys/kernel/tainted').read_text()))
def idle(h):return not h['taint'] and all(v=='suspended' for v in [*h['sensors'].values(),*h['platforms'].values()]) and all(v==dict(state='disabled',users=0) for v in h['rails'].values())
def wait_idle():
 deadline=time.monotonic()+8
 while time.monotonic()<deadline:
  h=health()
  if idle(h):return h
  time.sleep(.2)
 raise RuntimeError('Camera resources did not suspend')
class Msg(ctypes.Structure):_fields_=[('addr',ctypes.c_uint16),('flags',ctypes.c_uint16),('len',ctypes.c_uint16),('buf',ctypes.POINTER(ctypes.c_uint8))]
class Transfer(ctypes.Structure):_fields_=[('msgs',ctypes.POINTER(Msg)),('nmsgs',ctypes.c_uint32)]
save('preflight');before=subprocess.check_output(['dmesg']);consumers={};stopped=[];results={};private_reads={};plans=[];failure=None;restart_ok=True
try:
 if Path('/proc/sys/kernel/random/boot_id').read_bytes()!=Path('/var/lib/samurai/k305-geometry-r2/boot-id-private.txt').read_bytes():raise RuntimeError('Device restarted; inspect current bindings')
 wait_idle();consumers=services();plans=json.loads((root/'plans.json').read_text())['plans']
 save('stopping-consumers')
 for name in ['wireplumber','pipewire']:
  fd=os.pidfd_open(consumers[name]['pid'])
  try:
   signal.pidfd_send_signal(fd,signal.SIGTERM)
   if not select.select([fd],[],[],8)[0]:raise RuntimeError(name+' did not exit')
  finally:os.close(fd)
  stopped.append(name)
 wait_idle()
 for plan in plans:
  model=plan['model'];save('starting-power-owner',model=model)
  devices=[p for p in (Path('/sys/bus/i2c/drivers')/model).iterdir() if (p/'of_node').exists()]
  if len(devices)!=1:raise RuntimeError('Sensor binding not unique')
  device=Path('/sys/bus/i2c/devices')/devices[0].name;bus=int(device.name.split('-')[0]);address=plan['address7'];length=plan['read_bytes'];start=plan['start'];label=plan.get('label',model)
  if plan['operation']!='READ' or start<0 or length<=0 or start+length>65536 or plan['address_bytes']!=2 or plan['data_bytes']!=1:raise RuntimeError('Unsupported read map')
  if (Path('/sys/bus/i2c/devices')/f'{bus}-{address:04x}'/'driver').exists():raise RuntimeError('EEPROM has another bound owner')
  camera_id='/base'+str((device/'of_node').resolve()).split('/base',1)[1]
  path=root/('hold-'+model+'.log');camfd=None;fd=None;ret=None;error=None;reads=[]
  env=dict(os.environ)
  for key in list(env):
   if key.startswith('LIBCAMERA_'):env.pop(key)
  args=[str(root/'pipeline-fixture'),'/dev/media0','/usr/bin/cam','--camera',camera_id,'--stream','role=viewfinder,width=320,height=240,pixelformat=NV12','--capture=0']
  with path.open('xb') as log:
   child=subprocess.Popen(args,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   save('waiting-for-frame',model=model,holder_pid=child.pid)
   try:
    deadline=time.monotonic()+10
    while time.monotonic()<deadline:
     if child.poll() is not None:raise RuntimeError('Power owner exited before read')
     if b' seq: ' in path.read_bytes() and (device/'power/runtime_status').read_text().strip()=='active':break
     time.sleep(.05)
    else:raise TimeoutError('Standard cam did not produce a frame')
    # /proc/PID/task/PID/children requires an optional kernel configuration.
    # PPid from stat works on this kernel and still identifies our own child.
    children=[]
    for proc in Path('/proc').glob('[0-9]*'):
     try:
      fields=(proc/'stat').read_text().rsplit(')',1)[1].split()
      if fields[0]!='Z' and int(fields[1])==child.pid:children.append(proc.name)
     except (FileNotFoundError,ProcessLookupError):pass
    if len(children)!=1:raise RuntimeError('Power-owner child not unique')
    camfd=os.pidfd_open(int(children[0]));fd=os.open('/dev/i2c-'+str(bus),os.O_RDWR|os.O_CLOEXEC)
    funcs=ctypes.c_ulong();fcntl.ioctl(fd,0x0705,funcs)
    if not funcs.value&1:raise RuntimeError('Adapter lacks combined I2C transfers')
    deadline=time.monotonic()+25;save('reading',model=model,bus=bus)
    for index in [1,2]:
     out=bytearray()
     for offset in range(start,start+length,8):
      if child.poll() is not None or select.select([camfd],[],[],0)[0]:raise RuntimeError('Power owner stopped during read')
      if time.monotonic()>deadline:raise TimeoutError('EEPROM read timed out')
      count=min(8,start+length-offset);pointer=(ctypes.c_uint8*2)(offset>>8,offset&255);data=(ctypes.c_uint8*count)()
      # A two-byte address pointer followed by READ; no EEPROM data write.
      messages=(Msg*2)(Msg(address,0,2,pointer),Msg(address,1,count,data));transfer=Transfer(messages,2)
      if fcntl.ioctl(fd,0x0707,transfer)!=2:raise RuntimeError('Incomplete EEPROM transfer')
      out.extend(data)
     raw=bytes(out);(root/(label+f'-read{index}-private.bin')).write_bytes(raw);reads.append(dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    if reads[0]!=reads[1]:raise RuntimeError('Independent reads differ')
   except BaseException:
    error=traceback.format_exc();(root/('failure-'+model+'.txt')).write_text(error)
   finally:
    if fd is not None:os.close(fd)
    save('stopping-power-owner',model=model)
    if child.poll() is None:
     if camfd is not None and not select.select([camfd],[],[],0)[0]:signal.pidfd_send_signal(camfd,signal.SIGINT)
     else:child.send_signal(signal.SIGINT)
    try:ret=child.wait(timeout=60)
    finally:
     if camfd is not None:os.close(camfd)
  text=path.read_text(errors='replace');restored='FIXTURE_RESTORATION result=0' in text
  private_reads[label]=dict(model=model,bus=bus,address7=address,start=start,reads=reads)
  (root/'reads-private.json').write_text(json.dumps(private_reads,indent=2)+'\n')
  results[label]=dict(model=model,start_address=start,bytes_per_read=length,independent_reads=len(reads),duplicate_reads_equal=len(reads)==2 and reads[0]==reads[1],frames=len(re.findall(r' seq: ',text)),
   holder_exit=ret,holder_still_live=child.poll() is None,media_and_controls_restored=restored,error=error is not None)
  results[label]['passed']=error is None and ret==0 and restored and results[label]['duplicate_reads_equal']
  wait_idle()
except BaseException:
 failure=traceback.format_exc();(root/'failure-worker.txt').write_text(failure)
finally:
 save('restoring-consumers')
 try:
  wait_idle()
  for name in ['pipewire','wireplumber']:
   if name not in stopped:continue
   item=consumers[name];user=pwd.getpwuid(item['uid']);env=item['env'].copy();env.pop('PIPEWIRE_NOTIFICATION_FD',None)
   def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
   with (root/(name+'-restart.log')).open('wb') as log:
    child=subprocess.Popen(item['argv'],env=env,cwd=item['cwd'],preexec_fn=demote,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   time.sleep(.5)
   if child.poll() is not None:raise RuntimeError(name+' restart failed')
 except BaseException:
  restart_ok=False;(root/'failure-restore.txt').write_text(traceback.format_exc())
after=subprocess.check_output(['dmesg']);(root/'dmesg-after.txt').write_bytes(after)
faults={w.decode():after.count(w)-before.count(w) for w in [b'WARNING:',b'Oops:',b'CCI error',b'Stream stop failed:',b'Failed to disable stream on remote pad:',b'Missing SOF tag',b'Unhandled context fault']}
current=wait_idle();report=dict(stage=326,cameras=results,related_fault_delta=faults,health=current,services_restored=restart_ok,worker_failure=failure is not None,
 standard_cam_stream_owns_power=True,no_pixels_saved=True,no_eeprom_data_writes=True,no_values_applied=True,factory_checksum_not_claimed=True)
report['passed']=failure is None and len(results)==len(plans) and all(r['passed'] for r in results.values()) and restart_ok and idle(current) and not any(faults.values())
save('complete' if report['passed'] else 'failed',terminal=True,summary=report);print(json.dumps(report))
