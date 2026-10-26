# Appended to the reused package transaction's process/service helpers.
def default_env():
 env=os.environ.copy()
 for key in ['LIBCAMERA_CAMSS_VFE_PROFILE','LIBCAMERA_CAMSS-VFE_TUNING_FILE','LIBCAMERA_IPA_CONFIG_PATH','LIBCAMERA_IPA_MODULE_PATH','LIBCAMERA_PIPELINES_MATCH_LIST','LIBCAMERA_CAMSS_VFE_ENABLE','LIBCAMERA_IPA_FORCE_ISOLATION','LD_LIBRARY_PATH']:
  env.pop(key,None)
 env['LIBCAMERA_LOG_LEVELS']='*:INFO,CamssVfe:DEBUG,IPACamss:DEBUG'
 return env

def restore_profiles():
 for model,existed in backup_state.items():
  dest=directory/(model+'.yaml')
  if existed:
   temporary=dest.with_name(dest.name+'.k344-restore');shutil.copyfile(root/'backup'/dest.name,temporary);temporary.chmod(0o644);os.replace(temporary,dest)
  elif dest.exists():dest.unlink()

cases=json.loads((root/'cases.json').read_text());directory=Path('/etc/libcamera/ipa/camss-vfe')
consumers={};new_services={};stopped=False;changed=False;verified=False;rollback=False;failure=None;user_probe=None;captures={};backup_state={}
fault_words=[b'WARNING:',b'Oops:',b'CCI error',b'Stream stop failed:',b'Failed to disable stream on remote pad:',b'Missing SOF tag',b'Received wm done for unmapped index',b'Unhandled context fault']
before=subprocess.check_output(['dmesg']);save('preflight')
try:
 if Path('/proc/sys/kernel/random/boot_id').read_bytes()!=Path('/var/lib/samurai/k305-geometry-r2/boot-id-private.txt').read_bytes():raise RuntimeError('Device restarted')
 if Path('/proc/sys/kernel/tainted').read_text().strip()!='0':raise RuntimeError('Unexpected taint')
 note=hashlib.sha256(Path('/sys/module/qcom_camss/notes/.note.gnu.build-id').read_bytes()).hexdigest()
 if note!='0227d29bb5129e2fc69866529147b21b902d441c855f848fd5eaa3093c590297':raise RuntimeError('CAMSS baseline changed')
 consumers=services();wait_idle()
 # The installed stack has already been tested; only guard its required parser version.
 packages={}
 for block in Path('/lib/apk/db/installed').read_text().split('\n\n'):
  fields=dict(line.split(':',1) for line in block.splitlines() if ':' in line)
  if fields.get('P') in ['libcamera','libcamera-ipa']:packages[fields['P']]=fields['V']
 if packages!={'libcamera':'99990.7.2-r27','libcamera-ipa':'99990.7.2-r27'}:raise RuntimeError('Required r27 parser changed')
 (root/'backup').mkdir();directory.mkdir(parents=True,exist_ok=True)
 for source in sorted((root/'configs').glob('*.yaml')):
  dest=directory/source.name
  if dest.is_symlink():raise RuntimeError('Inspect existing profile symlink: '+str(dest))
  backup_state[source.stem]=dest.exists()
  if dest.exists():shutil.copyfile(dest,root/'backup'/dest.name)
 (root/'backup-state.json').write_text(json.dumps(backup_state)+'\n')
 save('stopping-consumers');stopped=True;stop_services(consumers);wait_idle()
 save('installing-private-profiles');changed=True
 for source in sorted((root/'configs').glob('*.yaml')):
  dest=directory/source.name;temporary=dest.with_name(dest.name+'.k344-tmp')
  shutil.copyfile(source,temporary);temporary.chmod(0o644);os.replace(temporary,dest)
 save('capturing-default-profiles')
 for label,item in cases.items():
  save('capturing-default-profiles',selection=label)
  model=item['model'];devices=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().startswith(model+' ')]
  if len(devices)!=1:raise RuntimeError('Sensor node not unique')
  app=[str(root/'pipeline-fixture'),'/dev/media0',str(root/'bin/lsc-aec-smoke'),model,'/dev/'+devices[0].name,str(root/label),item['output'],item['sensor_size'],str(item['test_pattern']),str(root/'oracles'/(label+'.bin'))]
  with (root/('capture-'+label+'.log')).open('xb') as log:
   child=subprocess.Popen(app,env=default_env(),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   save('capturing-default-profiles',selection=label,child_pid=child.pid)
   try:ret=child.wait(timeout=40)
   except subprocess.TimeoutExpired:child.send_signal(signal.SIGINT);ret=child.wait(timeout=10)
  text=(root/('capture-'+label+'.log')).read_text(errors='replace')
  captures[label]=dict(frames=text.count('CCM_FRAME '),settled_phases=text.count('settled=1'),
   probe_passed=' failed=0 result=0' in text,cleanup_restored='FIXTURE_RESTORATION result=0' in text,
   default_private_path_loaded=('Using tuning file '+str(directory/(model+'.yaml'))) in text)
  if ret or not all(captures[label][k] for k in ['probe_passed','cleanup_restored','default_private_path_loaded']):raise RuntimeError(label+' default capture failed')
 wait_idle()
 q=run(['cam','-l'],'enumeration',env=default_env());text=(q.stdout+q.stderr).decode(errors='replace')
 if text.count('for pipeline handler camss-vfe')!=4:raise RuntimeError('Expected four hardware cameras')
 model='imx319';device=next(p for p in Path('/sys/bus/i2c/drivers',model).iterdir() if (p/'of_node').exists())
 camera_id='/base'+str((device/'of_node').resolve()).split('/base',1)[1]
 run([str(root/'pipeline-fixture'),'/dev/media0',str(root/'bin/gst-hardware-probe'),camera_id,'640','480'],'installed-gstreamer',env=default_env(),timeout=30)
 wait_idle();save('restarting-consumers');restart(consumers,'new',new_services)
 item=new_services['pipewire'];env=item['env'].copy()
 user_probe=Path(env['XDG_RUNTIME_DIR'])/(root.name+'-pw-probe')
 with user_probe.open('xb') as out:out.write((root/'bin/pw-hardware-probe').read_bytes())
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
 if selected is None:raise RuntimeError('Wide PipeWire node not found')
 run([str(user_probe),selected[2].decode()],'installed-pipewire',env=env,preexec_fn=demote(item),timeout=25)
 wait_idle();current=subprocess.check_output(['dmesg'])
 if any(current.count(w)!=before.count(w) for w in fault_words) or Path('/proc/sys/kernel/tainted').read_text().strip()!='0':raise RuntimeError('Related fault during default capture')
 verified=True
except BaseException:
 failure=traceback.format_exc();(root/'failure.txt').write_text(failure)
finally:
 if not verified and stopped:
  try:
   save('rollback');stop_services(new_services or consumers);wait_idle()
   if changed:restore_profiles()
   new_services={};restart(consumers,'rollback',new_services);wait_idle();rollback=True
  except BaseException:(root/'rollback-failure.txt').write_text(traceback.format_exc())
 if user_probe and user_probe.exists():user_probe.unlink()
 after=subprocess.check_output(['dmesg']);(root/'dmesg-after.txt').write_bytes(after)
 faults={w.decode():after.count(w)-before.count(w) for w in fault_words}
 health={'platforms':{n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['acb3000.camss','ac4a000.cci','ac4b000.cci']},
  'rails':{(p/'name').read_text().strip():{'state':(p/'state').read_text().strip(),'users':int((p/'num_users').read_text())} for p in Path('/sys/class/regulator').glob('regulator.*') if (p/'name').read_text().startswith(('cam-main-','cam-front-','cam-rear-','cam-tele-'))}}
 service_pids={name:[int(p.name) for p in processes(name)] for name in ['pipewire','wireplumber']}
 restored=all(len(v)==1 for v in service_pids.values())
 report=dict(stage=344,configuration_installed=verified,rollback=rollback,failure=failure is not None,
  consumers_restored=restored,captures=captures,services=service_pids,fault_delta=faults,taint=int(Path('/proc/sys/kernel/tainted').read_text()),health=health,
  installed_core_and_ipa=True,default_ipa_lookup_used=True,explicit_profile_override_used=False,package_files_unchanged=True,kernel_unchanged=True)
 report['passed']=verified and restored and not any(faults.values()) and not report['taint'] and all(v=='suspended' for v in health['platforms'].values()) and all(v=={'state':'disabled','users':0} for v in health['rails'].values())
 save('complete' if report['passed'] else 'failed',terminal=True,summary=report);print(json.dumps(report))
