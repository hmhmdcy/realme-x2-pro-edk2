"""One paired module/APK transaction with an already exported matched rollback.

Normal sensor unbind only; shared CAMSS/CCI/PMIC drivers stay loaded.
Camera consumers stay stopped until a matching driver/framework pair is verified.
"""
from pathlib import Path
import hashlib,json,struct
import host
R=Path(__file__).resolve().parent
assert json.loads((R/'gain-rollback-validation.json').read_text())['phone_and_pc_copies_verified']
proof=json.loads((R/'current-module-build-validation.json').read_text())
raw=(host.PRIVATE/'current-module-build-r3/s5k3m5.ko').read_bytes()
assert hashlib.sha256(raw).hexdigest()==proof['sha256']
off=struct.unpack_from('<Q',raw,40)[0];size,count,strings=struct.unpack_from('<HHH',raw,58)
sections=[struct.unpack_from('<IIQQQQIIQQ',raw,off+i*size) for i in range(count)]
s=sections[strings];names=raw[s[4]:s[4]+s[5]]
note=next(raw[x[4]:x[4]+x[5]] for x in sections if names[x[0]:].split(b'\0',1)[0]==b'.note.gnu.build-id')
response=host.PRIVATE/'gain-install-response-private.log';assert not response.exists()
code=r'''
from pathlib import Path
import hashlib,json,os,pwd,select,signal,shutil,stat,subprocess,time,traceback
os.umask(0o077);r=Path('/var/lib/samurai');out=r/'k271-gain-transaction';stage=r/'k271-gain-candidates';backup=out/'backup'
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
 return all(Path('/sys/bus/i2c/devices',n,'power/runtime_status').read_text().strip()=='suspended' for n in ['7-0010','8-002d','9-0010']) and all(Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip()=='suspended' for n in ['ac4a000.cci','ac4b000.cci','acb3000.camss'])
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
   if (p/'comm').read_text().strip()==name and int((p/'status').read_text().split('Uid:',1)[1].split()[0])==10000:result.append(p)
  except OSError:continue
 return result
old=json.loads((out/'old-manifest-private.json').read_text());new=json.loads((out/'new-manifest-private.json').read_text())
services={x['name']:x for x in json.loads((out/'services-before-private.json').read_text())}
tree=Path('/usr/lib/modules')/os.uname().release;target=tree/'kernel/drivers/media/i2c/s5k3m5.ko';original=backup/str(target).lstrip('/')
device=Path('/sys/bus/i2c/devices/8-002d');driver=Path('/sys/bus/i2c/drivers/s5k3m5')
stopped=[];new_services=[];pair_verified=False;failure=None;rollback_verified=False;before=faults()
save()
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k270-work/boot-id-private.txt').read_bytes()
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and not any(before.values())
 assert Path('/lib/apk/db/installed').read_bytes()==(backup/'lib/apk/db/installed').read_bytes()
 assert Path('/etc/apk/world').read_bytes()==(backup/'etc/apk/world').read_bytes()
 assert sha(target)==sha(original)=='22315c6f3eb233add16e33658bd071dbc973499744b21323adf8b771c1552f72'
 assert sha(stage/'s5k3m5.ko')==__MODULE__
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
  assert not processes(name),'Unexpected daemon restart; inspect manager before mutation'
 wait_idle();open_fds=holders();(out/'camera-fd-holders-private.json').write_text(json.dumps(open_fds));assert not open_fds
 save(state='normal-sensor-unbind-submitted')
 (driver/'unbind').write_text('8-002d');state['module_unbound']=True;save(state='sensor-unbound')
 assert not (device/'driver').is_symlink()
 q=subprocess.run(['modprobe','-r','s5k3m5'],capture_output=True,timeout=20)
 (out/'unload-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0 and not Path('/sys/module/s5k3m5').exists()
 save(state='signed-package-transaction-submitted',packages_sent=True)
 with (out/'native-install-private.log').open('xb') as log:
  q=subprocess.run(['apk','--no-network','--repositories-file',str(out/'candidate-repositories.list'),'add','samurai-camera-stack=0.1.0-r15'],stdout=log,stderr=subprocess.STDOUT,timeout=60)
 assert q.returncode==0;verify_payload(new)
 save(state='new-packages-verified')
 temporary=target.with_name('s5k3m5.ko.k271-new');assert not temporary.exists();shutil.copyfile(stage/'s5k3m5.ko',temporary);temporary.chmod(0o644);os.replace(temporary,target)
 state['module_replaced']=True;save(state='new-module-file-installed')
 subprocess.run(['depmod','-a'],capture_output=True,check=True,timeout=30)
 assert subprocess.check_output(['modinfo','-F','vermagic','s5k3m5'],text=True).strip()==__VERMAGIC__
 subprocess.run(['modprobe','s5k3m5'],capture_output=True,check=True,timeout=20)
 assert (device/'driver').resolve().name=='s5k3m5'
 assert sha('/sys/module/s5k3m5/notes/.note.gnu.build-id')==__NOTE__
 node=next('/dev/'+p.name for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()=='s5k3m5 8-002d')
 controls=subprocess.check_output(['v4l2-ctl','-d',node,'--list-ctrls'],text=True);(out/'new-controls-private.txt').write_text(controls)
 line=next(x for x in controls.splitlines() if 'analogue_gain' in x);assert 'min=32 max=512 step=1 default=32' in line
 olddb=records((backup/'lib/apk/db/installed').read_bytes());newdb=records(Path('/lib/apk/db/installed').read_bytes());names={x['name'] for x in new['packages']}
 assert set(olddb)==set(newdb) and len(newdb)==961
 assert all(newdb[n]==v for n,v in olddb.items() if n not in names)
 for pkg in new['packages']:assert 'V:'+pkg['version'] in newdb[pkg['name']].splitlines()
 inventory={str(p.relative_to(tree)):sha(p) for p in tree.rglob('*.ko')};previous=json.loads((out/'module-inventory-before-private.json').read_text())
 assert inventory.keys()==previous.keys() and [n for n in inventory if inventory[n]!=previous[n]]==['kernel/drivers/media/i2c/s5k3m5.ko']
 repo=Path('/etc/apk/repositories.d/60-samurai-camera.list');repo.write_text('ndx file://'+str(stage/'forward/packages.adb')+'\n');repo.chmod(0o644)
 q=subprocess.run(['apk','--no-network','--repositories-file',str(out/'rollback-repositories.list'),'add','--simulate',*[x['name']+'='+x['version'] for x in old['packages']]],capture_output=True,text=True,timeout=30)
 (out/'rollback-simulate-private.log').write_text(q.stdout+q.stderr)
 assert q.returncode==0 and len([x for x in q.stdout.splitlines() if x.startswith('(') and 'Downgrading ' in x])==7
 pair_verified=True;save(state='matching-new-pair-verified')
except BaseException:
 failure=traceback.format_exc();(out/'failure-private.txt').write_text(failure);save(state='failure-restoration-pending')
 if state['module_unbound'] or state['module_replaced'] or state['packages_sent']:
  if (device/'driver').is_symlink():(driver/'unbind').write_text('8-002d')
  if Path('/sys/module/s5k3m5').exists():subprocess.run(['modprobe','-r','s5k3m5'],capture_output=True,check=True,timeout=20)
  if state['packages_sent']:
   with (out/'rollback-install-private.log').open('xb') as log:
    q=subprocess.run(['apk','--no-network','--repositories-file',str(out/'rollback-repositories.list'),'add',*[x['name']+'='+x['version'] for x in old['packages']]],stdout=log,stderr=subprocess.STDOUT,timeout=60)
   assert q.returncode==0
  for path in ['etc/apk/world','etc/apk/repositories.d/60-samurai-camera.list']:
   shutil.copyfile(backup/path,Path('/')/path)
  shutil.copyfile(original,target);target.chmod(0o644);subprocess.run(['depmod','-a'],capture_output=True,check=True,timeout=30)
  subprocess.run(['modprobe','s5k3m5'],capture_output=True,check=True,timeout=20)
  assert (device/'driver').resolve().name=='s5k3m5' and sha(target)==sha(original)
  verify_payload(old);rollback_verified=True;pair_verified=True;save(state='matching-original-pair-restored')
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
  (r/'k271-services-current-private.json').write_text(json.dumps(dict(boot_guard='/var/lib/samurai/k270-work/boot-id-private.txt',new_processes=new_services,matching_new_pair=not failure),indent=2)+'\n')
after=faults();delta={k:v-before[k] for k,v in after.items()}
report=dict(stage=271,paired_update_verified=pair_verified and not failure,rollback_verified=rollback_verified,failure=failure is not None,
 original_pair_retained=True,normal_sensor_unbind_used=state['module_unbound'],shared_camera_drivers_not_unloaded=True,
 new_module_sha256=sha(target),new_module_loaded_note_matches=not failure,five_framework_components='99990.7.2-r20' if not failure else '99990.7.2-r19',
 configuration_version='0.1.0-r15' if not failure else '0.1.0-r14',installed_package_count=961,other_954_package_records_preserved=not failure,
 other_773_modules_preserved=not failure,new_processes=new_services,desktop_processes_preserved=True,camera_idle=idle(),
 fault_delta=delta,taint=int(Path('/proc/sys/kernel/tainted').read_text()),no_flash_or_reboot=True,physical_fractional_gain_validation_pending=True)
save(state='verified' if not failure else 'failed-restored',terminal=True,exit_code=0 if not failure else 1)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''.replace('__MODULE__',repr(proof['sha256'])).replace('__VERMAGIC__',repr(proof['vermagic'])).replace('__NOTE__',repr(hashlib.sha256(note).hexdigest()))
response.write_bytes(b'SUBMISSION INTENT: inspect k271-gain-transaction before any repeat.\n')
q=host.ssh('python3 -',input=code.encode(),timeout=190,check=False)
response.write_bytes(q.stdout+q.stderr)
assert q.stdout and q.returncode==0,'Inspect the existing transaction and live processes; do not resubmit'
d=json.loads(q.stdout);(R/'gain-install-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
assert d['paired_update_verified'] and d['camera_idle'] and not any(d['fault_delta'].values()) and d['taint']==0
