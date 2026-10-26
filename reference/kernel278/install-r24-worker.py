
from pathlib import Path
import hashlib,json,os,pwd,select,signal,shutil,stat,subprocess,time,traceback
os.umask(0o077);r=Path('/var/lib/samurai');out=r/'k278-package-transaction';stage=r/'k278-package-candidates';backup=out/'backup'
marker=out/'transaction-state-private.json';assert not marker.exists()
state=dict(state='preflight',terminal=False,pid=os.getpid(),module_unbound=False,module_replaced=False,packages_sent=False)
def save(**kw):state.update(kw);marker.write_text(json.dumps(state,indent=2)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def identity(pid):return Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()[19]
def faults():
 b=subprocess.check_output(['dmesg']);return {k:b.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',fatal=b'fatal error received',modem=b'crash detected in modem').items()}
def verify_payload(manifest):
 for pkg in manifest['packages']:
  for name,item in pkg['files'].items():
   p=Path('/')/name
   if item['kind']=='symlink':assert p.is_symlink() and os.readlink(p)==item['target']
   else:assert not p.is_symlink() and sha(p)==item['sha256'] and stat.S_IMODE(p.stat().st_mode)==item['mode']
def records(raw):
 result={}
 for block in raw.decode().split('\n\n'):
  names=[l[2:] for l in block.splitlines() if l.startswith('P:')]
  if names:result[names[0]]=block
 return result
def idle():
 return all(Path('/sys/bus/i2c/devices',n,'power/runtime_status').read_text().strip()=='suspended' for n in ['6-0010','7-0010','8-002d','9-0010','6-0072']) and all(Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip()=='suspended' for n in ['ac4a000.cci','ac4b000.cci','acb3000.camss'])
def wait_idle():
 for _ in range(50):
  if idle():return
  time.sleep(.2)
 raise RuntimeError('Camera resources did not become idle')
def holders():
 result=[]
 for p in Path('/proc').glob('[0-9]*'):
  try:
   for fd in (p/'fd').iterdir():
    try:dest=os.readlink(fd)
    except OSError:continue
    if dest.startswith(('/dev/media','/dev/v4l-subdev','/dev/video')):result.append(dict(pid=int(p.name),target=dest))
  except OSError:continue
 return result
u=pwd.getpwuid(10000)
def demote():os.initgroups(u.pw_name,u.pw_gid);os.setgid(u.pw_gid);os.setuid(u.pw_uid)
def processes(name):
 result=[]
 for p in Path('/proc').glob('[0-9]*'):
  try:
   if (p/'comm').read_text().strip()==name and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z' and int((p/'status').read_text().split('Uid:',1)[1].split()[0])==10000:result.append(p)
  except OSError:continue
 return result
old=json.loads((out/'old-manifest-private.json').read_text());new=json.loads((out/'new-manifest-private.json').read_text())
services={x['name']:x for x in json.loads((out/'services-before-private.json').read_text())}
tree=Path('/usr/lib/modules')/os.uname().release
stopped=[];new_services=[];pair_verified=False;failure=None;rollback_verified=False;before=faults()
save()
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k276-work/boot-id-private.txt').read_bytes()
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and not any(before.values())
 assert Path('/lib/apk/db/installed').read_bytes()==(backup/'lib/apk/db/installed').read_bytes()
 assert Path('/etc/apk/world').read_bytes()==(backup/'etc/apk/world').read_bytes()
 assert all(p.read_text().strip()=='closed' for p in Path('/proc/asound').glob('card*/pcm*/sub*/status'))
 assert idle();verify_payload(old)
 for name,item in services.items():assert identity(item['pid'])==item['start_ticks']
 for name in ['pipewire','wireplumber']:
  q=subprocess.run(['rc-service','--user',name,'status'],preexec_fn=demote,env=services[name]['env'],capture_output=True,timeout=8)
  (out/(name+'-manager-status-private.log')).write_bytes(q.stdout+q.stderr)
  assert q.returncode==3 and b'stopped' in q.stdout,'Manager state differs; inspect before stopping daemons'
 save(state='stopping-camera-consumers')
 for name in ['wireplumber','pipewire']:
  item=services[name];fd=os.pidfd_open(item['pid']);assert identity(item['pid'])==item['start_ticks']
  try:signal.pidfd_send_signal(fd,signal.SIGTERM);assert select.select([fd],[],[],8)[0],name+' did not terminate normally'
  finally:os.close(fd)
  stopped.append(name)
  for _ in range(50):
   if not processes(name):break
   time.sleep(.1)
  assert not processes(name),'Unexpected live daemon restart; inspect manager before mutation'
 wait_idle();open_fds=holders();(out/'camera-fd-holders-private.json').write_text(json.dumps(open_fds));assert not open_fds
 save(state='signed-package-transaction-submitted',packages_sent=True)
 with (out/'native-install-private.log').open('xb') as log:
  q=subprocess.run(['apk','--no-network','--repositories-file',str(out/'candidate-repositories.list'),'add','samurai-camera-stack=0.1.0-r19'],stdout=log,stderr=subprocess.STDOUT,timeout=60)
 assert q.returncode==0;verify_payload(new)
 save(state='new-packages-verified')
 olddb=records((backup/'lib/apk/db/installed').read_bytes());newdb=records(Path('/lib/apk/db/installed').read_bytes());names={x['name'] for x in new['packages']}
 assert set(olddb)==set(newdb) and len(newdb)==961
 assert all(newdb[n]==v for n,v in olddb.items() if n not in names)
 for pkg in new['packages']:assert 'V:'+pkg['version'] in newdb[pkg['name']].splitlines()
 inventory={str(p.relative_to(tree)):sha(p) for p in tree.rglob('*.ko')};previous=json.loads((out/'module-inventory-before-private.json').read_text())
 assert inventory==previous and len(inventory)==776
 repo=Path('/etc/apk/repositories.d/60-samurai-camera.list');repo.write_text('ndx file://'+str(stage/'forward/packages.adb')+'\n');repo.chmod(0o644)
 q=subprocess.run(['apk','--no-network','--repositories-file',str(out/'rollback-repositories.list'),'add','--simulate',*[x['name']+'='+x['version'] for x in old['packages']]],capture_output=True,text=True,timeout=30)
 (out/'rollback-simulate-private.log').write_text(q.stdout+q.stderr)
 assert q.returncode==0 and len([x for x in q.stdout.splitlines() if x.startswith('(') and 'Downgrading ' in x])==7
 pair_verified=True;save(state='matching-new-pair-verified')
except BaseException:
 failure=traceback.format_exc();(out/'failure-private.txt').write_text(failure);save(state='failure-restoration-pending')
 if state['packages_sent']:
  with (out/'rollback-install-private.log').open('xb') as log:
   q=subprocess.run(['apk','--no-network','--repositories-file',str(out/'rollback-repositories.list'),'add',*[x['name']+'='+x['version'] for x in old['packages']]],stdout=log,stderr=subprocess.STDOUT,timeout=60)
  assert q.returncode==0
  for path in ['etc/apk/world','etc/apk/repositories.d/60-samurai-camera.list']:
   shutil.copyfile(backup/path,Path('/')/path)
  verify_payload(old);rollback_verified=True;pair_verified=True;save(state='matching-original-packages-restored')
 else:pair_verified=True
finally:
 if pair_verified:
  for name in ['pipewire','wireplumber']:
   if name not in stopped:continue
   assert not processes(name),'Inspect unexpected daemon before restarting'
   env=services[name]['env'].copy();env.pop('PIPEWIRE_NOTIFICATION_FD',None)
   log=(out/(name+'-restart-private.log')).open('xb')
   kwargs=dict(env=env,cwd=services[name]['cwd'],preexec_fn=demote,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   if name=='pipewire':
    readfd,writefd=os.pipe();env['PIPEWIRE_NOTIFICATION_FD']=str(writefd)
    child=subprocess.Popen(['/usr/bin/'+name],pass_fds=(writefd,),**kwargs);os.close(writefd)
    assert select.select([readfd],[],[],10)[0] and os.read(readfd,64),'PipeWire readiness not received';os.close(readfd)
   else:child=subprocess.Popen(['/usr/bin/'+name],**kwargs)
   assert child.poll() is None
   new_services.append(dict(name=name,pid=child.pid,start_ticks=identity(child.pid)))
   log.close()
  deadline=time.monotonic()+12
  while 'wireplumber' in stopped and time.monotonic()<deadline:
   found=processes('wireplumber');assert len(found)==1
   maps=(found[0]/'maps').read_text()
   if '/usr/lib/spa-0.2/libcamera/libspa-libcamera.so' in maps and '/usr/lib/libcamera.so.0.7.2' in maps:break
   time.sleep(.2)
  if 'wireplumber' in stopped:
   assert '/usr/lib/libcamera.so.0.7.2' in maps and not any('libcamera' in line and '(deleted)' in line for line in maps.splitlines())
  wait_idle()
  for name in ['phosh','phoc']:assert identity(services[name]['pid'])==services[name]['start_ticks']
  (r/'k278-services-current-private.json').write_text(json.dumps(dict(boot_guard='/var/lib/samurai/k276-work/boot-id-private.txt',new_processes=new_services,matching_new_pair=not failure),indent=2)+'\n')
after=faults();delta={k:v-before[k] for k,v in after.items()}
report=dict(stage=278,packages_verified=pair_verified and not failure,rollback_verified=rollback_verified,failure=failure is not None,
 framework_version='99990.7.2-r24' if not failure else '99990.7.2-r23',configuration_version='0.1.0-r19' if not failure else '0.1.0-r18',
 installed_package_count=961,other_954_package_records_preserved=not failure,all_776_modules_preserved=not failure,
 new_processes=new_services,desktop_processes_preserved=True,camera_idle=idle(),fault_delta=delta,
 taint=int(Path('/proc/sys/kernel/tainted').read_text()),no_flash_or_reboot=True,no_driver_unbind_or_unload=True,
 physical_autofocus_validation_pending=True)
save(state='verified' if not failure else 'failed-restored',terminal=True,exit_code=0 if not failure else 1)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
