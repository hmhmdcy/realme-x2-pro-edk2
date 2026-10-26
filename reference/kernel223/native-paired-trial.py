"""Temporary normal module replacement. Always restore installed CAMSS and policy."""
from pathlib import Path
import fcntl,hashlib,json,os,pwd,re,select,signal,struct,subprocess,threading,time
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k223-paired-sof-trial';assert not out.exists();out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k223-baseline/boot-id-private.txt').read_bytes()
assert Path('/sys/firmware/devicetree/base/model').read_bytes()==b'Realme X2 Pro (RMX1931CN)\0' and os.uname().version.startswith('#183 ')
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
stage=root/'k223-sof-modules';candidate=stage/'qcom-camss-candidate.ko';original=Path(subprocess.check_output(['modinfo','-n','qcom-camss'],text=True).strip())
assert hashlib.sha256(candidate.read_bytes()).hexdigest()=='fae1ed40da4e2751c081aca3a990a5a3c44de47599883a045340b9f62f54803e'
assert hashlib.sha256(original.read_bytes()).hexdigest()=='82cbc0528a76858ac57e149bdb540d14630112d74213384303960eead684fe58'
(out/'qcom-camss-original.ko').write_bytes(original.read_bytes())
def note(path):
 data=Path(path).read_bytes();offset=struct.unpack_from('<Q',data,40)[0];size,count,strings=struct.unpack_from('<HHH',data,58)
 hs=[struct.unpack_from('<IIQQQQIIQQ',data,offset+i*size) for i in range(count)];s=hs[strings];names=data[s[4]:s[4]+s[5]]
 matches=[data[h[4]:h[4]+h[5]] for h in hs if names[h[0]:].split(b'\0',1)[0]==b'.note.gnu.build-id'];assert len(matches)==1;return matches[0]
loaded=Path('/sys/module/qcom_camss/notes/.note.gnu.build-id');original_note=note(original);candidate_note=note(candidate);assert loaded.read_bytes()==original_note
camss=Path('/sys/bus/platform/devices/acb3000.camss');driver=Path('/sys/bus/platform/drivers/qcom-camss')
def process_list(name):
 result=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   if (p/'comm').read_text().strip()==name and int((p/'status').read_text().split('Uid:',1)[1].split()[0])==10000:result.append(p)
  except OSError:pass
 return result
preserved={name:{p.name:(p/'stat').read_text().split(') ',1)[1].split()[19] for p in process_list(name)} for name in ['pipewire','phosh','phoc','gnome-session-b']};assert all(len(v)==1 for v in preserved.values())
wp=process_list('wireplumber');assert len(wp)==1;wp=wp[0]
argv=[x.decode() for x in (wp/'cmdline').read_bytes().split(b'\0') if x];assert argv==['/usr/bin/wireplumber'] and os.readlink(wp/'exe')==argv[0]
env={k.decode():v.decode() for item in (wp/'environ').read_bytes().split(b'\0') if b'=' in item for k,v in [item.split(b'=',1)]}
assert 'DBUS_SESSION_BUS_ADDRESS' in env and not any(k in env for k in ['LD_LIBRARY_PATH','LIBCAMERA_IPA_MODULE_PATH','LIBCAMERA_IPA_PROXY_PATH','LIBCAMERA_IPA_CONFIG_PATH'])
(out/'policy-before-private.json').write_text(json.dumps(dict(pid=int(wp.name),argv=argv,environment=env,preserved=preserved),indent=2)+'\n')
def nodes():return {(p/'name').read_text().strip():p.name for p in Path('/sys/class/video4linux').glob('v4l-subdev*')}
def formats():
 result={}
 for name,node in nodes().items():
  fd=os.open('/dev/'+node,os.O_RDWR|os.O_CLOEXEC)
  try:
   for pad in range(32):
    buf=bytearray(88);struct.pack_into('II',buf,0,1,pad)
    try:fcntl.ioctl(fd,0xc0585604,buf,True)
    except OSError as error:assert error.errno in [22,25];break
    result[(name,pad)]=bytes(buf)
  finally:os.close(fd)
 return result
def links():
 text=subprocess.check_output(['media-ctl','-d','/dev/media0','-p'],text=True);result=[];entity=pad=None
 for line in text.splitlines():
  m=re.match(r'^- entity \d+: (.*?) \(',line)
  if m:entity=m[1];continue
  m=re.match(r'\s+pad(\d+):',line)
  if m:pad=int(m[1]);continue
  m=re.match(r'\s+-> "(.*?)":(\d+) \[(.*?)\]',line)
  if m and 'IMMUTABLE' not in m[3]:result.append((entity,pad,m[1],int(m[2]),int('ENABLED' in m[3])))
 return result
def video_fds():
 result=[]
 for process in Path('/proc').iterdir():
  if not process.name.isdigit():continue
  try:
   for fd in (process/'fd').iterdir():
    try:
     value=os.readlink(fd)
     if value.startswith(('/dev/media','/dev/video','/dev/v4l-subdev')):result.append((process.name,fd.name,value))
    except OSError:pass
  except OSError:pass
 return result
def command(args):
 p=subprocess.run(args,capture_output=True,timeout=30);(out/('command-'+str(len(state['commands']))+'-private.log')).write_bytes(p.stdout+p.stderr);state['commands'].append(dict(action=args[0],exit=p.returncode));save();assert p.returncode==0
def save():(out/'state-private.json').write_text(json.dumps(state,indent=2)+'\n')
state=dict(phase='preflight',commands=[]);save();saved_formats=formats();saved_links=links();assert saved_formats
(out/'formats-before-private.json').write_text(json.dumps({name+'|'+str(pad):data.hex() for (name,pad),data in saved_formats.items()},indent=2)+'\n')
(out/'links-before-private.json').write_text(json.dumps(saved_links,indent=2)+'\n')
def setlink(link,enabled):
 a,p,b,q,_=link;subprocess.run(['media-ctl','-d','/dev/media0','--links',f'"{a}":{p} -> "{b}":{q} [{enabled}]'],capture_output=True,check=True,timeout=10)
def restore_graph():
 for link in links():setlink(link,0)
 current_nodes=nodes()
 def rank(item):return next((i for i,prefix in enumerate(['imx471','msm_csiphy','msm_csid','msm_ispif','msm_vfe']) if item[0][0].startswith(prefix)),5),item[0][1]
 for (name,pad),data in sorted(saved_formats.items(),key=rank):
  fd=os.open('/dev/'+current_nodes[name],os.O_RDWR|os.O_CLOEXEC)
  try:
   current=bytearray(88);struct.pack_into('II',current,0,1,pad);fcntl.ioctl(fd,0xc0585604,current,True)
   if bytes(current)!=data:fcntl.ioctl(fd,0xc0585605,bytearray(data),True)
  finally:os.close(fd)
 for link in saved_links:
  if link[4]:setlink(link,1)
 assert formats()==saved_formats and sorted(links())==sorted(saved_links)
eventfd=None;event_thread=None;thread_stop=threading.Event();events=[];event_errors=[];test=None;test_data=None;failure=None
before=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(before)
try:
 state['phase']='policy-stop-submitted';save();os.kill(int(wp.name),signal.SIGTERM)
 for _ in range(50):
  if not wp.exists():break
  time.sleep(.1)
 assert not wp.exists() and not process_list('wireplumber')
 assert not video_fds() and (camss/'power/runtime_status').read_text().strip()=='suspended'
 state['phase']='original-unbind-submitted';save();(driver/'unbind').write_text('acb3000.camss');assert not (camss/'driver').exists()
 command(['rmmod','qcom_camss']);assert not loaded.exists()
 state['phase']='candidate-load-submitted';save();command(['insmod',str(candidate)]);assert loaded.read_bytes()==candidate_note and (camss/'driver').exists()
 state['phase']='candidate-loaded';save()
 tests=[]
 for kind,width,height in [('raw',1928,1088),('rgb',1920,1088),('raw',2304,1728),('rgb',2296,1728)]:
  label=f'{kind}-{width}x{height}'
  events=[];event_errors=[];thread_stop.clear()
  eventfd=os.open('/dev/'+nodes()['msm_vfe0_rdi0'],os.O_RDWR|os.O_NONBLOCK|os.O_CLOEXEC)
  subscription=bytearray(32);struct.pack_into('I',subscription,0,4);fcntl.ioctl(eventfd,0x4020565a,subscription,True)
  def observe():
   poll=select.poll();poll.register(eventfd,select.POLLPRI)
   while not thread_stop.is_set():
    if not poll.poll(50):continue
    while True:
     data=bytearray(136)
     try:fcntl.ioctl(eventfd,0x80885659,data,True)
     except OSError as error:
      if error.errno in [2,11]:break
      event_errors.append(error.errno);return
     assert struct.unpack_from('I',data,0)[0]==4
     events.append(dict(frame_sequence=struct.unpack_from('I',data,8)[0],queue_sequence=struct.unpack_from('I',data,76)[0],timestamp_ns=struct.unpack_from('q',data,80)[0]*1000000000+struct.unpack_from('q',data,88)[0]))
  event_thread=threading.Thread(target=observe);event_thread.start()
  state.update(phase='paired-capture-live',case=label);save()
  test=subprocess.Popen(['python3',str(stage/'paired-runner.py'),kind,'0',str(width),str(height),'1','system'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
  stdout,stderr=test.communicate(timeout=50)
  (out/(label+'-runner-stdout-private.json')).write_bytes(stdout);(out/(label+'-runner-stderr-private.txt')).write_bytes(stderr)
  thread_stop.set();event_thread.join(timeout=3);assert not event_thread.is_alive();event_thread=None
  os.close(eventfd);eventfd=None
  (out/(label+'-events-private.json')).write_text(json.dumps(events,indent=2)+'\n')
  assert test.returncode==0;test_data=json.loads(stdout);assert test_data['program_exit']==0 and len(test_data['frames'])==16
  assert not event_errors and events
  tests.append(dict(case=label,frames=test_data['frames'],events=events,client_exit=test_data['program_exit']))
  (out/'all-cases-private.json').write_text(json.dumps(tests,indent=2)+'\n')

finally:
 if test is not None and test.poll() is None:
  os.killpg(test.pid,signal.SIGINT);test.communicate(timeout=12)
 thread_stop.set()
 if event_thread:event_thread.join(timeout=3);assert not event_thread.is_alive()
 if eventfd is not None:os.close(eventfd)
 (out/'events-private.json').write_text(json.dumps(events,indent=2)+'\n')
 state['event_reader_errors']=event_errors;state['phase']='original-restore-pending';save()
 assert not video_fds()
 if loaded.exists() and loaded.read_bytes()==candidate_note:
  if (camss/'driver').exists():(driver/'unbind').write_text('acb3000.camss')
  command(['rmmod','qcom_camss'])
 if not loaded.exists():command(['modprobe','qcom-camss'])
 assert loaded.read_bytes()==original_note
 if not (camss/'driver').exists():(driver/'bind').write_text('acb3000.camss')
 restore_graph()
 if not process_list('wireplumber'):
  user=pwd.getpwuid(10000)
  def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
  with (out/'policy-restart-private.log').open('wb') as log:child=subprocess.Popen(argv,env=env,preexec_fn=demote,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  time.sleep(2);assert child.poll() is None
 assert len(process_list('wireplumber'))==1
 for name,identities in preserved.items():assert {p.name:(p/'stat').read_text().split(') ',1)[1].split()[19] for p in process_list(name)}==identities
 state['phase']='original-restored';save()
after=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(after)
faults={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()}
time.sleep(2);assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and not any(faults.values())
assert not event_errors and test_data is not None
cases=[]
for case in tests:
 events=case['events'];by_id={x['frame_sequence']:x for x in events};frames=case['frames']
 pairs=[f['timestamp_ns']-by_id[f['buffer_sequence']]['timestamp_ns'] for f in frames if f['buffer_sequence'] in by_id]
 cases.append(dict(case=case['case'],capture_frames=len(frames),frame_sync_events=len(events),consecutive_event_sequence=all(b['frame_sequence']==a['frame_sequence']+1 for a,b in zip(events,events[1:])),all_buffers_have_observed_sof=len(pairs)==len(frames),buffer_sequences=[f['buffer_sequence'] for f in frames],maximum_capture_gap=max(b['buffer_sequence']-a['buffer_sequence'] for a,b in zip(frames,frames[1:])),minimum_sof_to_completion_ms=min(pairs)/1000000 if pairs else None,maximum_sof_to_completion_ms=max(pairs)/1000000 if pairs else None))
assert len(cases)==4
r=dict(stage=223,temporary_candidate_trial=True,candidate_module_loaded_and_verified=True,cases=cases,original_camss_loaded_note_verified=True,original_module_file_unchanged=True,graph_and_formats_restored_before_policy=True,wireplumber_restored=True,desktop_and_pipewire_identities_preserved=True,taint=0,fault_delta=faults,missing_sof_tag_messages=after.count(b'Missing SOF tag')-before.count(b'Missing SOF tag'),manual_api_and_control_snapshots_not_yet_accepted=True,no_flash_or_reboot=True)
state.update(phase='verified-restored',result=r);save();(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
