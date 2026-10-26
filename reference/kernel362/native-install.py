"""Install the tested package/module pair, retaining an offline rollback."""
from pathlib import Path
import hashlib,json,os,pwd,re,select,signal,shutil,subprocess,sys,time,traceback
root=Path(sys.argv[1]);state={'stage':362,'pid':os.getpid(),'terminal':False,'phase':'preflight'}
marker=root/'state.json'
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
def versions():
 result={}
 for block in Path('/lib/apk/db/installed').read_text().split('\n\n'):
  fields=dict(line.split(':',1) for line in block.splitlines() if ':' in line)
  if fields.get('P') in proof['packages']:result[fields['P']]=fields['V']
 return result
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
proof=json.loads((root/'proof.json').read_text());consumers={};new_services={};stopped=False;changed=False;packages_sent=False;verified=False;rollback=False;failure=None;user_probe=None;module_changed=False;profiles_changed=False;default_results={}
before=subprocess.check_output(['dmesg']);save('preflight');target=None
try:
 if Path('/proc/sys/kernel/random/boot_id').read_bytes()!=Path(proof['boot_guard']).read_bytes():raise RuntimeError('Device restarted')
 if Path('/proc/sys/kernel/tainted').read_text().strip()!='0':raise RuntimeError('Unexpected taint')
 if versions()!=proof['old_packages']:raise RuntimeError('Installed package baseline changed')
 if sha('/sys/module/qcom_camss/notes/.note.gnu.build-id')!=proof['module_note_sha256']:raise RuntimeError('CAMSS baseline changed')
 consumers=services();wait_idle()
 target=Path(subprocess.check_output(['modinfo','-n','qcom_camss'],text=True).strip())
 if target.suffix!='.ko':raise RuntimeError('Expected existing uncompressed module')
 if subprocess.check_output(['modinfo','-F','vermagic',str(target)])!=subprocess.check_output(['modinfo','-F','vermagic',str(root/'qcom-camss.ko')]):raise RuntimeError('Module ABI mismatch')
 profile_names=['etc/libcamera/ipa/camss-vfe/'+m+'.yaml' for m in ['s5kgw1','imx471','imx319','s5k3m5']]
 if not all((Path('/')/name).is_file() for name in profile_names):raise RuntimeError('Expected344 defaults')
 backup=root/'backup';backup.mkdir()
 for name in ['etc/apk/world','etc/apk/repositories.d/60-samurai-camera.list',str(target.relative_to('/')),*profile_names]:
  p=backup/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(Path('/')/name,p)
 for kind in ['forward','rollback']:(root/(kind+'.list')).write_text('ndx file://'+str(root/'repository'/kind/'packages.adb')+'\n')
 run(['apk','--no-network','--repositories-file',str(root/'forward.list'),'add','--simulate','samurai-camera-stack=0.1.0-r24'],'simulate',timeout=40)
 save('stopping-consumers');stopped=True;stop_services(consumers);wait_idle()
 save('installing-packages');packages_sent=True
 run(['apk','--no-network','--repositories-file',str(root/'forward.list'),'add','samurai-camera-stack=0.1.0-r24'],'packages',timeout=90)
 if versions()!=proof['packages']:raise RuntimeError('Package versions differ')
 module_changed=True
 run(['rmmod','qcom_camss'],'unload-old-module')
 temp=target.with_name(target.name+'.k362-tmp');shutil.copyfile(root/'qcom-camss.ko',temp);temp.chmod(0o644);os.replace(temp,target)
 run(['modprobe','qcom_camss'],'load-tested-module')
 if sha('/sys/module/qcom_camss/notes/.note.gnu.build-id')!=proof['candidate_note_sha256']:raise RuntimeError('Loaded candidate differs')
 profiles_changed=True
 for name in profile_names:
  dest=Path('/')/name;temp=dest.with_name(dest.name+'.k362-tmp');shutil.copyfile(root/'profiles'/dest.name,temp);temp.chmod(0o644);os.replace(temp,dest)
 # Inserted into the native transaction after the matched module and profiles.
 default_cases=json.loads((root/'default-cases.json').read_text())
 default_results={}
 for label,item in default_cases.items():
  model=item['model']
  nodes=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().startswith(model+' ')]
  if len(nodes)!=1:raise RuntimeError('Default sensor not unique: '+model)
  env=dict(os.environ,LIBCAMERA_IPA_FORCE_ISOLATION='1',LIBCAMERA_LOG_LEVELS='*:INFO,CamssVfe:DEBUG,IPACamss:DEBUG')
  for key in ['LIBCAMERA_CAMSS_VFE_PROFILE','LIBCAMERA_CAMSS_VFE_ENABLE','LIBCAMERA_IPA_MODULE_PATH','LIBCAMERA_IPA_PROXY_PATH','LD_LIBRARY_PATH','LIBCAMERA_PIPELINES_MATCH_LIST']:env.pop(key,None)
  q=run([str(root/'pipeline-fixture'),'/dev/media0',str(root/'bin/adaptation-smoke'),model,'/dev/'+nodes[0].name,item['sensor_size'],str(item['test_pattern'])],
        'default-'+label,timeout=40,env=env)
  text=(q.stdout+q.stderr).decode(errors='replace')
  pids=re.findall(r'ADAPT_PID value=(\d+)',text);ipa_pids=set(re.findall(r'IPA stats pid=(\d+)',text))
  good=(len(pids)==1 and bool(ipa_pids) and all(pid!=pids[0] for pid in ipa_pids) and
        ' failed=0 result=0' in text and text.count('ADAPT_PHASE ')==5 and text.count('GAMMA_APPLIED ')==1 and
        '/etc/libcamera/ipa/camss-vfe/'+model+'.yaml' in text and
        'ADAPT_LIBRARY path=/usr/lib/libcamera.so.0.7.2' in text and
        'ADAPT_LIBRARY path=/usr/lib/libcamera-base.so.0.7.2' in text and 'FIXTURE_RESTORATION result=0' in text)
  default_results[label]=dict(frames=text.count('ADAPT_FRAME '),phases=text.count('ADAPT_PHASE '),gamma_ack=text.count('GAMMA_APPLIED '),isolated=True,standard_private_path=True,passed=good)
  if not good:raise RuntimeError('Installed default request check failed: '+label)
 wait_idle()

 q=run(['cam','-l'],'enumeration');enumeration=(q.stdout+q.stderr).decode(errors='replace')
 if enumeration.count('for pipeline handler camss-vfe')!=4:raise RuntimeError('Default hardware enumeration failed')
 model='imx319';devices=[p for p in Path('/sys/bus/i2c/drivers',model).iterdir() if (p/'of_node').exists()]
 camera_id='/base'+str((devices[0]/'of_node').resolve()).split('/base',1)[1]
 run([str(root/'pipeline-fixture'),'/dev/media0',str(root/'bin/gst-hardware-probe'),camera_id,'640','480'],'installed-gstreamer',timeout=30)
 wait_idle();save('restarting-consumers');restart(consumers,'new',new_services)
 item=new_services['pipewire'];env=item['env'].copy()
 user_probe=Path(env['XDG_RUNTIME_DIR'])/(root.name+'-pw-probe')
 with user_probe.open('xb') as output:output.write((root/'bin/pw-hardware-probe').read_bytes())
 user_probe.chmod(0o755);user=pwd.getpwuid(item['uid']);os.chown(user_probe,user.pw_uid,user.pw_gid)
 nodes=[];deadline=time.monotonic()+8
 while time.monotonic()<deadline:
  q=run([str(user_probe),'--list'],'pw-enumeration',env=env,preexec_fn=demote(item))
  nodes=re.findall(rb'PW_NODE id=(\d+) name=(\S+) serial=(\S+) path=(\S+)',q.stdout)
  if len(nodes)==4:break
  time.sleep(.2)
 if len(nodes)!=4:raise RuntimeError('Expected four PipeWire camera nodes')
 node_name='libcamera_input.'+re.sub(r'[^A-Za-z0-9_.-]','_',camera_id)
 selected=next((n for n in nodes if n[3].decode()==camera_id or n[1].decode()==node_name),None)
 if selected is None:raise RuntimeError('Requested PipeWire camera node not found')
 run([str(user_probe),selected[2].decode()],'installed-pipewire',env=env,preexec_fn=demote(item),timeout=25)
 wait_idle()
 current=subprocess.check_output(['dmesg'])
 if any(current.count(w)!=before.count(w) for w in [b'WARNING:',b'Oops:',b'CCI error',b'Stream stop failed:',b'Failed to disable stream on remote pad:',b'Missing SOF tag',b'Unhandled context fault']) or Path('/proc/sys/kernel/tainted').read_text().strip()!='0':raise RuntimeError('Related kernel fault during installed capture')
 Path('/etc/apk/repositories.d/60-samurai-camera.list').write_text('ndx file://'+str(root/'repository/forward/packages.adb')+'\n')
 verified=True;save('verified')
except BaseException:
 failure=traceback.format_exc();(root/'failure.txt').write_text(failure)
finally:
 if not verified and stopped:
  try:
   save('rollback')
   stop_services(new_services or consumers)
   wait_idle()
   if profiles_changed:
    for name in profile_names:
     dest=Path('/')/name;temp=dest.with_name(dest.name+'.k362-tmp');shutil.copyfile(root/'backup'/name,temp);os.replace(temp,dest)
   if module_changed:
    if Path('/sys/module/qcom_camss').exists():run(['rmmod','qcom_camss'],'rollback-unload')
    temp=target.with_name(target.name+'.k362-tmp');shutil.copyfile(root/'backup'/str(target.relative_to('/')),temp);os.replace(temp,target)
    run(['modprobe','qcom_camss'],'rollback-module')
   if packages_sent:
    run(['apk','--no-network','--repositories-file',str(root/'rollback.list'),'add',*[k+'='+v for k,v in proof['old_packages'].items()]],'rollback-packages',timeout=90)
   for name in ['etc/apk/world','etc/apk/repositories.d/60-samurai-camera.list']:shutil.copyfile(root/'backup'/name,Path('/')/name)
   new_services={};restart(consumers,'rollback',new_services);wait_idle();rollback=True
  except BaseException:(root/'rollback-failure.txt').write_text(traceback.format_exc())
 if user_probe and user_probe.exists():user_probe.unlink()
 after=subprocess.check_output(['dmesg']);(root/'dmesg-after.txt').write_bytes(after)
 faults={w.decode():after.count(w)-before.count(w) for w in [b'WARNING:',b'Oops:',b'CCI error',b'Stream stop failed:',b'Failed to disable stream on remote pad:',b'Missing SOF tag',b'Unhandled context fault']}
 report=dict(stage=362,installed=verified,rollback=rollback,failure=failure is not None,packages=versions(),module_unchanged=False,module_stage=348,private_defaults_updated=verified,default_checks=default_results,kernel_image_unchanged=True,
  loaded_camss_note_sha256=sha('/sys/module/qcom_camss/notes/.note.gnu.build-id') if Path('/sys/module/qcom_camss/notes/.note.gnu.build-id').exists() else None,
  fault_delta=faults,taint=int(Path('/proc/sys/kernel/tainted').read_text()))
 report['camera_runtime']={name:Path('/sys/bus/platform/devices',name,'power/runtime_status').read_text().strip() for name in ['acb3000.camss','ac4a000.cci','ac4b000.cci']}
 report['services']={name:[int(p.name) for p in processes(name)] for name in ['pipewire','wireplumber']}
 report['passed']=verified and not any(faults.values()) and not report['taint'] and all(value=='suspended' for value in report['camera_runtime'].values()) and all(len(value)==1 for value in report['services'].values())
 save('complete' if report['passed'] else 'failed',terminal=True,summary=report);print(json.dumps(report))
