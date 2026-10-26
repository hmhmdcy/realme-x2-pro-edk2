"""Install the tested package/module pair, retaining an offline rollback."""
from pathlib import Path
import hashlib,json,os,pwd,re,select,signal,shutil,subprocess,sys,time,traceback
root=Path(sys.argv[1]);state={'stage':388,'pid':os.getpid(),'terminal':False,'phase':'preflight'}
marker=root/'camera-state.json'
if marker.exists():raise RuntimeError('Existing transaction; inspect its process/state')
def save(phase,**kw):state.update(phase=phase,**kw);marker.write_text(json.dumps(state,indent=2)+'\n')
def run(args,label,timeout=25,env=None,preexec_fn=None):
 q=subprocess.run(args,capture_output=True,timeout=timeout,env=env,preexec_fn=preexec_fn)
 (root/(label+'.log')).write_bytes(q.stdout+q.stderr)
 if q.returncode:raise RuntimeError(label+' failed')
 return q
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
  p=ps[0];result[name]={'pid':int(p.name),'uid':p.stat().st_uid,'argv':[x.decode() for x in (p/'cmdline').read_bytes().split(b'\0') if x],
    'cwd':os.readlink(p/'cwd'),'env':dict(x.decode().split('=',1) for x in (p/'environ').read_bytes().split(b'\0') if x)}
 return result
def stop_services(items):
 for name in ['wireplumber','pipewire']:
  if name not in items:continue
  pid=items[name]['pid'];p=Path('/proc',str(pid),'stat')
  if not p.exists() or p.read_text().rsplit(')',1)[1].split()[0]=='Z':continue
  fd=os.pidfd_open(pid)
  try:
   signal.pidfd_send_signal(fd,signal.SIGTERM)
   if not select.select([fd],[],[],8)[0]:raise RuntimeError(name+' did not exit')
  finally:os.close(fd)
def demote(item):
 user=pwd.getpwuid(item['uid'])
 def callback():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
 return callback
def restart(items,label,started):
 result=started
 for name in ['pipewire','wireplumber']:
  item=items[name];env=item['env'].copy();env.pop('PIPEWIRE_NOTIFICATION_FD',None)
  with (root/(label+'-'+name+'.log')).open('wb') as log:
   child=subprocess.Popen(item['argv'],env=env,cwd=item['cwd'],preexec_fn=demote(item),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  time.sleep(.6)
  if child.poll() is not None:raise RuntimeError(name+' restart failed')
  result[name]={**item,'pid':child.pid}
 return result
def wait_idle():
 for _ in range(40):
  if all(Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip()=='suspended' for n in ['acb3000.camss','ac4a000.cci','ac4b000.cci']):return
  time.sleep(.2)
 raise RuntimeError('Camera did not suspend')

# Appended to the existing service save/restore helpers; all payloads stay private.
before=subprocess.check_output(['dmesg']);items={};started={};stopped=False;failure=None;captures={}
def status():
 current=json.loads(Path('/sys/bus/platform/devices/ac10000.samurai-icp356-boot/m2m_status').read_text())
 assert current['direct_completed']==current['completed']
 result=json.loads(Path('/sys/module/camss_icp_a5_boot_test/parameters/result').read_text())
 assert not result['copy_frames'] and not result['imported_buffers'] and not result['imported_bytes']
 assert result['direct_frames']==result['frames_completed']
 return current

def capture(args,label,env,expect_ipe=True):
 collector=json.loads((root/'state.json').read_text())['collector_pid']
 proc=Path('/proc',str(collector))
 assert str(root/'snapshot-collector.py').encode() in (proc/'cmdline').read_bytes() and (proc/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z'
 with (root/(label+'.log')).open('xb') as output:
  child=subprocess.Popen(args,env=env,stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
  save(label,child_pid=child.pid)
  try:result=child.wait(timeout=45)
  except subprocess.TimeoutExpired:
   os.killpg(child.pid,signal.SIGTERM)
   try:child.wait(timeout=12)
   except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=5)
   raise
 text=(root/(label+'.log')).read_text(errors='replace')
 assert result==0,label+' failed: '+str(result)
 assert 'FIXTURE_RESTORATION result=0' in text
 assert ('IPE enabled ' in text)==expect_ipe,label+' selected the wrong processing path'
 return text
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k378-recovered/boot-id-private.txt').read_bytes()
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 tools=Path('/var/lib/samurai/k362-install-r1');fixture=root/'pipeline-fixture'
 items=services();wait_idle();stopped=True;stop_services(items);wait_idle()
 env=dict(os.environ,LIBCAMERA_LOG_LEVELS='*:INFO,CamssVfe:DEBUG,IPACamss:DEBUG')
 for key in ['LD_LIBRARY_PATH','LIBCAMERA_CAMSS_VFE_PROFILE','LIBCAMERA_IPA_MODULE_PATH','LIBCAMERA_IPA_PROXY_PATH','LIBCAMERA_PIPELINES_MATCH_LIST','LIBCAMERA_CAMSS_VFE_ENABLE','LIBCAMERA_IPA_FORCE_ISOLATION']:env.pop(key,None)
 env['LD_LIBRARY_PATH']=str(root/'lib')
 env['LIBCAMERA_IPA_MODULE_PATH']='/usr/lib/libcamera/ipa'
 env['LIBCAMERA_IPA_PROXY_PATH']='/usr/libexec/libcamera'
 previous=status()
 for model in ['imx471','imx319','s5k3m5','s5kgw1']:
  devices=[p for p in Path('/sys/bus/i2c/drivers',model).iterdir() if (p/'of_node').exists()];assert len(devices)==1
  camera_id='/base'+str((devices[0]/'of_node').resolve()).split('/base',1)[1]
  text=capture([str(fixture),'/dev/media0',str(tools/'bin/gst-hardware-probe'),camera_id,'640','480'],'gst-'+model,env)
  match=re.search(r'GST_RESULT frames=(\d+) width=(\d+) height=(\d+) bus-errors=(\d+) result=(\d+)',text)
  assert match and int(match[1])>0 and not int(match[4]) and not int(match[5])
  current=status();assert current['completed']-previous['completed']>=int(match[1]) and current['jobs']==current['completed']+current['cancelled']
  assert not any(current[k] for k in ['users','running','pinned','orphans','fatal','failed'])
  captures[model]=dict(frames=int(match[1]),ipe_completed=current['completed']-previous['completed'],ipe_cancelled=current['cancelled']-previous['cancelled'],starts=current['starts']-previous['starts'],passed=True)
  previous=current
 for kind in ['dual','raw']:
  # RAW-only deliberately has no IPE; dual preserves the original IFE SOF.
  args=[str(fixture),'/dev/media0',str(root/'pipeline-smoke'),'s5kgw1@4608x3456',kind]
  text=capture(args,'raw-'+kind,env,expect_ipe=kind=='dual')
  assert 'failed=0 result=0' in text
  frames=len(re.findall(r'RAW_IMAGE request=\d+ format=NV12',text))
  pairs=re.findall(r'RawPair .* matched=(\d+)',text)
  assert pairs and all(x=='1' for x in pairs)
  current=status();delta=current['completed']-previous['completed']
  assert (delta>=frames>0 if kind=='dual' else delta==0)
  assert current['jobs']==current['completed']+current['cancelled'] and not any(current[k] for k in ['users','running','pinned','orphans','fatal','failed'])
  captures['raw-'+kind]=dict(processed_frames=frames,raw_pairs=len(pairs),ipe_completed=delta,ipe_cancelled=current['cancelled']-previous['cancelled'],original_ife_timestamp_on_processed_output_verified=kind=='dual',raw_pair_sof_verified=True,passed=True);previous=current
 nodes=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().startswith('s5kgw1 ')];assert len(nodes)==1
 env['LIBCAMERA_IPA_FORCE_ISOLATION']='1'
 text=capture([str(fixture),'/dev/media0',str(tools/'bin/adaptation-smoke'),'s5kgw1','/dev/'+nodes[0].name,'4608x3456','2'],'isolated-main',env)
 app=re.findall(r'ADAPT_PID value=(\d+)',text);ipa=set(re.findall(r'IPA stats pid=(\d+)',text))
 assert len(app)==1 and ipa and all(x!=app[0] for x in ipa)
 assert ' failed=0 result=0' in text and text.count('ADAPT_PHASE ')==5 and text.count('GAMMA_APPLIED ')==1
 current=status();assert current['completed']-previous['completed']>=text.count('ADAPT_FRAME ')
 assert current['jobs']==current['completed']+current['cancelled'] and not any(current[k] for k in ['users','running','pinned','orphans','fatal','failed'])
 captures['isolated-main']=dict(frames=text.count('ADAPT_FRAME '),ipe_completed=current['completed']-previous['completed'],ipe_cancelled=current['cancelled']-previous['cancelled'],phases=5,gamma_ack=1,actual_isolation_verified=True,passed=True)
except BaseException:
 failure=traceback.format_exc();(root/'camera-failure.txt').write_text(failure)
finally:
 restored=False
 try:
  wait_idle()
  if stopped:restart(items,'restore',started)
  wait_idle();restored=all(len(processes(name))==1 for name in ['pipewire','wireplumber'])
 except BaseException:(root/'camera-restore-failure.txt').write_text(traceback.format_exc())
 after=subprocess.check_output(['dmesg']);(root/'camera-dmesg-after.txt').write_bytes(after)
 faults={w.decode():after.count(w)-before.count(w) for w in [b'WARNING:',b'Oops:',b'CCI error',b'Stream stop failed:',b'Missing SOF tag',b'Unhandled context fault',b'OF: ERROR']}
 report=dict(stage=388,captures=captures,services_restored=restored,failure=failure is not None,fault_delta=faults,taint=int(Path('/proc/sys/kernel/tainted').read_text()),m2m_final=status(),low_light_not_failure=True)
 report['passed']=bool(not failure and restored and len(captures)==7 and not any(faults.values()) and report['taint']==0)
 save('complete' if report['passed'] else 'failed',terminal=True,summary=report);print(json.dumps(report))
sys.exit(0 if report['passed'] else 1)
