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
  LIBCAMERA_IPA_MODULE_PATH=str(root/'ipa'),LD_LIBRARY_PATH=str(root/'lib'))
 for key in ['LIBCAMERA_CAMSS_VFE_ENABLE','LIBCAMERA_PIPELINES_MATCH_LIST','LIBCAMERA_IPA_FORCE_ISOLATION']:env.pop(key,None)
 app=[str(root/'pipeline-fixture'),'/dev/media0',str(root/'bin/gamma-smoke'),model,'/dev/'+devices[0].name,str(root/label),
  item['output'],item['sensor_size'],str(item['test_pattern']),str(root/'profiles'/(selection+'-phase-oracle-private.bin'))]
 with (root/('capture-'+label+'.log')).open('xb') as log:
  child=subprocess.Popen(app,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  save('capturing',selection=label,child_pid=child.pid)
  try:ret=child.wait(timeout=40)
  except subprocess.TimeoutExpired:child.send_signal(signal.SIGINT);ret=child.wait(timeout=10)
 text=(root/('capture-'+label+'.log')).read_text(errors='replace')
 if 'FIXTURE_RESTORATION result=0' not in text:raise RuntimeError(label+' graph restoration failed')
 return ret,text
try:
 if Path('/proc/sys/kernel/random/boot_id').read_bytes()!=Path('/var/lib/samurai/k305-geometry-r2/boot-id-private.txt').read_bytes():raise RuntimeError('Device restarted')
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
 # A configured override must fail clearly on338, never report applied Gamma.
 if (root/'old-kernel-reference.json').exists():negative=json.loads((root/'old-kernel-reference.json').read_text())
 else:
  ret,text=capture('imx319-factory-0','old-kernel')
  negative=dict(nonzero_exit=ret!=0,no_gamma_ack='GAMMA_APPLIED ' not in text,no_images='GAMMA_FRAME ' not in text,
   explicit_start_error='START_STATUS status=-' in text,graph_restored=True)
 if not all(negative.values()):raise RuntimeError('Old kernel rejection was not explicit and clean')
 wait_idle();save('unloading-deployed');run(['rmmod','qcom_camss'],'unload-deployed');changed=True
 run(['insmod',str(root/'qcom-camss.ko')],'load-candidate')
 if hashlib.sha256(Path('/sys/module/qcom_camss/notes/.note.gnu.build-id').read_bytes()).hexdigest()!=proof['module_note_sha256']:raise RuntimeError('Candidate module differs')
 for selection in models:
  ret,text=capture(selection,selection)
  captures[selection]=dict(frames=text.count('GAMMA_FRAME '),settled_phases=text.count('settled=1'),
   probe_passed=ret==0 and ' failed=0 result=0' in text,gamma_acknowledged='GAMMA_APPLIED ' in text,cleanup_restored=True)
  if not captures[selection]['probe_passed'] or not captures[selection]['gamma_acknowledged']:raise RuntimeError(selection+' capture failed')
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
 report=dict(stage=349,failure=failure is not None,deployment_restored=restored,captures=captures,old_kernel_rejection=negative,
  fault_delta=faults,taint=int(Path('/proc/sys/kernel/tainted').read_text()),health=health,temporary_kernel_and_userspace=True,installed_files_unchanged=True)
 report['old_kernel_rejection_reused']=(root/'old-kernel-reference.json').exists()
 report['passed']=not failure and restored and len(captures)==len(models) and all(negative.values()) and not any(faults.values()) and not report['taint'] and all(v=='suspended' for v in health['platforms'].values()) and all(v==dict(state='disabled',users=0) for v in health['rails'].values())
 save('complete' if report['passed'] else 'failed',terminal=True,summary=report);print(json.dumps(report))
