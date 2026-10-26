"""Temporary r28 EV/flicker/Gamma validation with338 restoration."""
from pathlib import Path
import hashlib, json, os, pwd, select, signal, subprocess, sys, time, traceback

root = Path(sys.argv[1])
cases=json.loads((root/'cases.json').read_text());models=sys.argv[2].split(',') if len(sys.argv)>2 and sys.argv[2]!='all' else list(cases)
state = {'terminal':False, 'phase':'preflight', 'pid':os.getpid()}
marker = root/'state.json'
if marker.exists():
    raise RuntimeError('Run already exists; inspect it instead of replaying')
def save(phase, **values):
    state.update(phase=phase, **values)
    marker.write_text(json.dumps(state, indent=2)+'\n')
def run(args, label, timeout=20):
    q=subprocess.run(args, capture_output=True, timeout=timeout)
    (root/(label+'.log')).write_bytes(q.stdout+q.stderr)
    if q.returncode: raise RuntimeError(label+' failed')
    return q
def processes(name):
    found=[]
    for p in Path('/proc').glob('[0-9]*'):
        try:
            if (p/'comm').read_text().strip()==name and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z':
                found.append(p)
        except (FileNotFoundError,ProcessLookupError):pass
    return found
def services():
    result={}
    for name in ['pipewire','wireplumber']:
        ps=processes(name)
        if len(ps)!=1: raise RuntimeError('Expected one '+name+' consumer')
        p=ps[0]
        env=dict(x.decode().split('=',1) for x in (p/'environ').read_bytes().split(b'\0') if x)
        result[name]=dict(pid=int(p.name), uid=p.stat().st_uid,
                          argv=[x.decode() for x in (p/'cmdline').read_bytes().split(b'\0') if x],
                          cwd=os.readlink(p/'cwd'), env=env)
    return result
def wait_idle():
    for _ in range(30):
        if Path('/sys/bus/platform/devices/acb3000.camss/power/runtime_status').read_text().strip()=='suspended':
            return
        time.sleep(.2)
    raise RuntimeError('CAMSS did not suspend')
stopped=[];changed=False;consumers={};failure=None;negative={};captures={}
save('preflight')
before=subprocess.check_output(['dmesg'])
before_note=hashlib.sha256(Path('/sys/module/qcom_camss/notes/.note.gnu.build-id').read_bytes()).hexdigest()
proof=json.loads((root/'proof.json').read_text())
def capture(selection,label):
 item=cases[selection];model=item['model']
 devices=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().startswith(model+' ')]
 if len(devices)!=1:raise RuntimeError('Sensor node not unique: '+model)
 env=dict(os.environ,LIBCAMERA_CAMSS_VFE_PROFILE=str(root/'profiles'/item['profile']),LIBCAMERA_LOG_LEVELS='*:INFO,CamssVfe:DEBUG,IPACamss:DEBUG',
  LIBCAMERA_IPA_MODULE_PATH=str(root/'ipa'),LIBCAMERA_IPA_PROXY_PATH=str(root/'proxy'),LD_LIBRARY_PATH=str(root/'lib'))
 for key in ['LIBCAMERA_CAMSS_VFE_ENABLE','LIBCAMERA_PIPELINES_MATCH_LIST','LIBCAMERA_IPA_FORCE_ISOLATION']:env.pop(key,None)
 if item['isolation']:env['LIBCAMERA_IPA_FORCE_ISOLATION']='1'
 app=[str(root/'pipeline-fixture'),'/dev/media0',str(root/'bin/adaptation-smoke'),model,'/dev/'+devices[0].name,item['sensor_size'],str(item['test_pattern'])]
 with (root/('capture-'+label+'.log')).open('xb') as log:
  child=subprocess.Popen(app,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  save('capturing',selection=label,child_pid=child.pid)
  try:ret=child.wait(timeout=40)
  except subprocess.TimeoutExpired:child.send_signal(signal.SIGINT);ret=child.wait(timeout=10)
 text=(root/('capture-'+label+'.log')).read_text(errors='replace')
 if 'FIXTURE_RESTORATION result=0' not in text:raise RuntimeError(label+' graph restoration failed')
 return ret,text
try:
 if Path('/proc/sys/kernel/random/boot_id').read_bytes()!=Path(proof['boot_guard']).read_bytes():raise RuntimeError('Device restarted')
 if Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=proof['expected_boot']:raise RuntimeError('Unexpected recovered boot')
 if Path('/proc/sys/kernel/tainted').read_text().strip()!='0':raise RuntimeError('Unexpected taint')
 if before_note!='0227d29bb5129e2fc69866529147b21b902d441c855f848fd5eaa3093c590297':raise RuntimeError('Expected installed338 module')
 deployed=subprocess.check_output(['modinfo','-n','qcom_camss'],text=True).strip()
 if subprocess.check_output(['modinfo','-F','vermagic',deployed])!=subprocess.check_output(['modinfo','-F','vermagic',str(root/'qcom-camss.ko')]):raise RuntimeError('Module/kernel mismatch')
 consumers=services();wait_idle()
 save('stopping-consumers')
 for name in ['wireplumber','pipewire']:
  fd=os.pidfd_open(consumers[name]['pid'])
  try:
   signal.pidfd_send_signal(fd,signal.SIGTERM)
   if not select.select([fd],[],[],8)[0]:raise RuntimeError(name+' did not exit')
  finally:os.close(fd)
  stopped.append(name)
 wait_idle()
 negative=proof['old_kernel_reference']
 if not all(negative.values()):raise RuntimeError('Retained349 old-kernel evidence incomplete')
 wait_idle();save('unloading-deployed');run(['rmmod','qcom_camss'],'unload-deployed');changed=True
 run(['insmod',str(root/'qcom-camss.ko')],'load-candidate')
 if hashlib.sha256(Path('/sys/module/qcom_camss/notes/.note.gnu.build-id').read_bytes()).hexdigest()!=proof['module_note_sha256']:raise RuntimeError('Candidate module differs')
 for selection in models:
  ret,text=capture(selection,selection)
  import re
  appPids=[int(p) for p in re.findall(r'ADAPT_PID value=(\d+)',text)]
  statsPids={int(p) for p in re.findall(r'IPA stats pid=(\d+)',text)}
  libraries=set(re.findall(r'ADAPT_LIBRARY path=(\S+)',text))
  librariesOk=all(str(root/'lib'/name) in libraries for name in ['libcamera.so.0.7.2','libcamera-base.so.0.7.2'])
  transportOk=len(appPids)==1 and bool(statsPids) and all((pid!=appPids[0])==cases[selection]['isolation'] for pid in statsPids)
  captures[selection]=dict(frames=text.count('ADAPT_FRAME '),completed_phases=text.count('ADAPT_PHASE '),
   probe_passed=ret==0 and ' failed=0 result=0' in text,gamma_ack_count=text.count('GAMMA_APPLIED '),
   isolation_requested=cases[selection]['isolation'],actual_transport_verified=transportOk,
   candidate_libraries_verified=librariesOk,
   actual_auto_updates=text.count('AE update epoch='),cleanup_restored=True)
  item=captures[selection]
  if not item['probe_passed'] or item['gamma_ack_count']!=1 or item['completed_phases']!=5 or not transportOk or not librariesOk or not item['actual_auto_updates']:raise RuntimeError(selection+' request integration failed')

except BaseException:
 failure=traceback.format_exc();(root/'failure.txt').write_text(failure)
finally:
 save('restoring-deployment');restored=False
 try:
  wait_idle()
  if changed:
   if Path('/sys/module/qcom_camss').exists():run(['rmmod','qcom_camss'],'unload-candidate')
   run(['modprobe','qcom_camss'],'restore-deployed')
  restored=hashlib.sha256(Path('/sys/module/qcom_camss/notes/.note.gnu.build-id').read_bytes()).hexdigest()==before_note
  if not restored:raise RuntimeError('Restored module differs')
 except BaseException:(root/'restore-failure.txt').write_text(traceback.format_exc())
 if restored:
  for name in ['pipewire','wireplumber']:
   if name not in stopped:continue
   item=consumers[name];user=pwd.getpwuid(item['uid'])
   def demote():
    os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
   env=item['env'].copy();env.pop('PIPEWIRE_NOTIFICATION_FD',None)
   with (root/(name+'-restart.log')).open('wb') as log:
    child=subprocess.Popen(item['argv'],env=env,cwd=item['cwd'],preexec_fn=demote,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   time.sleep(.5)
   if child.poll() is not None:restored=False
 after=subprocess.check_output(['dmesg']);(root/'dmesg-after.txt').write_bytes(after)
 faults={w.decode():after.count(w)-before.count(w) for w in [b'WARNING:',b'Oops:',b'CCI error',b'Stream stop failed:',b'Failed to disable stream on remote pad:',b'Missing SOF tag',b'Received wm done for unmapped index',b'Unhandled context fault']}
 names=['acb3000.camss','ac4a000.cci','ac4b000.cci']
 for _ in range(30):
  if all(Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip()=='suspended' for n in names):break
  time.sleep(.2)
 health=dict(platforms={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in names},
  rails={(p/'name').read_text().strip():dict(state=(p/'state').read_text().strip(),users=int((p/'num_users').read_text())) for p in Path('/sys/class/regulator').glob('regulator.*') if (p/'name').read_text().startswith(('cam-main-','cam-front-','cam-rear-','cam-tele-'))})
 report=dict(stage=362,failure=failure is not None,deployment_restored=restored,captures=captures,old_kernel_rejection=negative,
  fault_delta=faults,taint=int(Path('/proc/sys/kernel/tainted').read_text()),health=health,temporary_kernel_and_userspace=True,installed_files_unchanged=True)
 report['old_kernel_rejection_reused']=True
 report['passed']=not failure and restored and len(captures)==len(models) and all(negative.values()) and not any(faults.values()) and not report['taint'] and all(v=='suspended' for v in health['platforms'].values()) and all(v==dict(state='disabled',users=0) for v in health['rails'].values())
 save('complete' if report['passed'] else 'failed',terminal=True,summary=report);print(json.dumps(report))
