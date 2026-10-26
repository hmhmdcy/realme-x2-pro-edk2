"""One boot-guarded sensor-only transaction with verified rollback and daemon restart."""
from pathlib import Path
import hashlib,json,os,pwd,re,select,signal,shutil,subprocess,sys,time,traceback
os.umask(0o077)
root=Path(sys.argv[1]);assert re.fullmatch(r'/var/lib/samurai/k305-geometry-r[3-9][0-9]*',str(root))
marker=root/'transaction-state-private.json';assert not marker.exists()
pre=json.loads((root/'preflight-private.json').read_text())
proof=json.loads((root/'install-proof-private.json').read_text())
services=pre['services'];target=Path(pre['module_path']);tree=target.parents[4]
assert tree==Path('/usr/lib/modules')/os.uname().release
original=root/'backup'/str(target).lstrip('/')
device=Path('/sys/bus/i2c/devices')/pre['device'];driver=Path('/sys/bus/i2c/drivers/s5k3m5')
state=dict(stage=305,terminal=False,phase='preflight',pid=os.getpid(),
 start_ticks=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19],
 unbind_submitted=False,module_replaced=False)
def save(phase=None,**kw):
 if phase:state['phase']=phase
 state.update(kw);p=root/'transaction-state-next-private.json';p.write_text(json.dumps(state,indent=2)+'\n');p.replace(marker)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def identity(pid):return Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()[19]
def fault_counts():
 data=subprocess.check_output(['dmesg'])
 return {k:data.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu_fault=b'gpu fault:',fatal=b'fatal error received',modem=b'crash detected in modem').items()}
def health():
 sensors={}
 for name in ['s5kgw1','s5k3m5','imx319','imx471','lc898219xi']:
  rows=[p for p in Path('/sys/bus/i2c/drivers',name).iterdir() if p.is_symlink() and re.fullmatch(r'\d+-[0-9a-f]{4}',p.name)]
  assert len(rows)==1
  sensors[name]=(rows[0]/'power/runtime_status').read_text().strip()
 platforms={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['acb3000.camss','ac4a000.cci','ac4b000.cci']}
 rails={}
 for p in Path('/sys/class/regulator').glob('regulator.*'):
  n=(p/'name').read_text().strip()
  if n.startswith(('cam-main-','cam-front-','cam-rear-','cam-tele-')):
   rails[n]={k:(p/k).read_text().strip() for k in ['state','num_users']}
 return dict(sensors=sensors,platforms=platforms,rails=rails,taint=int(Path('/proc/sys/kernel/tainted').read_text()))
def is_idle(h):
 return len(h['sensors'])==5 and len(h['rails'])==9 and not h['taint'] and all(v=='suspended' for v in [*h['sensors'].values(),*h['platforms'].values()]) and all(v['state']=='disabled' and v['num_users']=='0' for v in h['rails'].values())
def wait_idle():
 for _ in range(40):
  h=health()
  if is_idle(h):return h
  time.sleep(.2)
 raise RuntimeError('Camera resources did not become idle')
def processes(name):
 result=[]
 for p in Path('/proc').glob('[0-9]*'):
  try:
   if (p/'comm').read_text().strip()==name and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z':result.append(p)
  except (FileNotFoundError,ProcessLookupError):pass
 return result
def holders():
 result=[]
 for p in Path('/proc').glob('[0-9]*'):
  try:
   for fd in (p/'fd').iterdir():
    try:dest=os.readlink(fd)
    except OSError:continue
    if dest.startswith(('/dev/media','/dev/v4l-subdev','/dev/video')):result.append(dict(pid=int(p.name),target=dest))
  except OSError:pass
 return result
def run(args,label,timeout=20):
 q=subprocess.run(args,capture_output=True,timeout=timeout)
 (root/(label+'-private.log')).write_bytes(q.stdout+q.stderr)
 assert q.returncode==0,label+' failed'
 return q
def replace_module(source,label):
 temporary=target.with_name('s5k3m5.ko.k305-'+label);assert not temporary.exists()
 shutil.copyfile(source,temporary);temporary.chmod(0o644);os.replace(temporary,target)
def verify_original():
 assert sha(target)==pre['original_sha256']
 assert (device/'driver').resolve()==driver and sha('/sys/module/s5k3m5/notes/.note.gnu.build-id')==pre['loaded_note_sha256']
u=pwd.getpwuid(10000)
def demote():os.initgroups(u.pw_name,u.pw_gid);os.setgid(u.pw_gid);os.setuid(u.pw_uid)
stopped=[];new_services=[];verified=False;rollback=False;failure=None;restart_failure=None;geometry=None
before_faults=fault_counts();before_health=health();save()
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'boot-id-private.txt').read_bytes()
 assert is_idle(before_health);verify_original()
 assert sha(original)==pre['original_sha256']
 assert sha(root/'payload/s5k3m5.ko')==proof['new_sha256']
 assert subprocess.check_output(['modinfo','-F','intree',str(root/'payload/s5k3m5.ko')],text=True).strip()=='Y'
 assert subprocess.check_output(['modinfo','-F','vermagic',str(root/'payload/s5k3m5.ko')],text=True).strip()==proof['vermagic']
 assert all(p.read_text().strip()=='closed' for p in Path('/proc/asound').glob('card*/pcm*/sub*/status'))
 for item in services.values():assert identity(item['pid'])==item['start_ticks']
 for name in ['pipewire','wireplumber']:
  q=subprocess.run(['rc-service','--user',name,'status'],preexec_fn=demote,env=services[name]['env'],capture_output=True,timeout=8)
  assert q.returncode==3 and b'stopped' in q.stdout,'Unexpected service manager state'
 save('stopping-consumers')
 for name in ['wireplumber','pipewire']:
  item=services[name];fd=os.pidfd_open(item['pid'])
  try:
   assert identity(item['pid'])==item['start_ticks']
   signal.pidfd_send_signal(fd,signal.SIGTERM)
   assert select.select([fd],[],[],8)[0],name+' did not exit'
  finally:os.close(fd)
  stopped.append(name);assert not processes(name),'Unexpected daemon restart'
 wait_idle();fds=holders();(root/'fd-holders-private.json').write_text(json.dumps(fds));assert not fds
 save('normal-unbind-submitted',unbind_submitted=True)
 (driver/'unbind').write_text(pre['device']);assert not (device/'driver').is_symlink()
 save('sensor-unbound')
 run(['modprobe','-r','s5k3m5'],'unload')
 assert not Path('/sys/module/s5k3m5').exists()
 replace_module(root/'payload/s5k3m5.ko','new');save('new-file-installed',module_replaced=True)
 run(['depmod','-a'],'depmod',30);run(['modprobe','s5k3m5'],'load')
 assert (device/'driver').resolve()==driver
 assert sha('/sys/module/s5k3m5/notes/.note.gnu.build-id')==proof['new_note_sha256']
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 node=next('/dev/'+p.name for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()=='s5k3m5 '+pre['device'])
 geometry=json.loads(run([str(root/'payload/sensor-geometry'),node],'geometry').stdout)
 assert geometry['selection_checks']==8 and geometry['crop']==[0,0,4208,3120]
 enum=run(['cam','-l'],'libcamera-enumeration')
 camera_id='/base'+str((device/'of_node').resolve()).split('/base',1)[1]
 assert camera_id.encode() in enum.stdout
 props=run(['cam','-c',camera_id,'-p'],'libcamera-properties')
 assert b'Property: Model = s5k3m5' in props.stdout and b'Property: PixelArraySize = 4208x3120' in props.stdout
 assert b'Property: PixelArrayActiveAreas = [ (0, 0)/4208x3120 ]' in props.stdout
 assert not any(b's5k3m5' in line and any(word in line for word in [b'CROP_DEFAULT',b'Sensor kernel driver needs to be fixed',b'Failed to retrieve the sensor crop']) for line in enum.stderr.splitlines())
 inventory={str(p.relative_to(tree)):sha(p) for p in tree.rglob('*.ko')}
 old=json.loads((root/'module-inventory-before-private.json').read_text())
 assert inventory.keys()==old.keys() and [n for n in inventory if inventory[n]!=old[n]]==['kernel/drivers/media/i2c/s5k3m5.ko']
 for path in ['lib/apk/db/installed','etc/apk/world']:assert Path('/'+path).read_bytes()==(root/'backup'/path).read_bytes()
 verified=True;save('new-module-and-geometry-verified')
except BaseException:
 failure=traceback.format_exc();(root/'failure-private.txt').write_text(failure);save('failure-rollback-pending')
 if state['unbind_submitted']:
  if (device/'driver').is_symlink():(driver/'unbind').write_text(pre['device'])
  if Path('/sys/module/s5k3m5').exists():run(['modprobe','-r','s5k3m5'],'rollback-unload')
  replace_module(original,'rollback');run(['depmod','-a'],'rollback-depmod',30);run(['modprobe','s5k3m5'],'rollback-load')
  verify_original();rollback=True
 verified=True
finally:
 if verified:
  try:
   for name in ['pipewire','wireplumber']:
    if name not in stopped:continue
    assert not processes(name)
    item=services[name];env=item['env'].copy();env.pop('PIPEWIRE_NOTIFICATION_FD',None)
    with (root/(name+'-restart-private.log')).open('xb') as log:
     kwargs=dict(env=env,cwd=item['cwd'],preexec_fn=demote,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
     if name=='pipewire':
      readfd,writefd=os.pipe();env['PIPEWIRE_NOTIFICATION_FD']=str(writefd)
      child=subprocess.Popen(item['argv'],pass_fds=(writefd,),**kwargs);os.close(writefd)
      try:assert select.select([readfd],[],[],10)[0] and os.read(readfd,64)
      finally:os.close(readfd)
     else:child=subprocess.Popen(item['argv'],**kwargs)
    assert child.poll() is None
    new_services.append(dict(name=name,pid=child.pid,start_ticks=identity(child.pid)))
   time.sleep(2)
   for item in new_services:assert identity(item['pid'])==item['start_ticks'] and processes(item['name'])
   for name in ['phoc','phosh']:assert identity(services[name]['pid'])==services[name]['start_ticks']
   wait_idle()
  except BaseException:
   restart_failure=traceback.format_exc();(root/'restart-failure-private.txt').write_text(restart_failure)
after_health=health();after_faults=fault_counts();delta={k:after_faults[k]-v for k,v in before_faults.items()}
report=dict(stage=305,new_boot_baseline=True,kernel_build=298,new_module_verified=verified and failure is None,
 rollback_verified=rollback,failure=failure is not None,restart_failure=restart_failure is not None,
 geometry=geometry,new_module_sha256=sha(target),new_services=new_services,
 before=before_health,after=after_health,resources_restored=before_health==after_health,
 fault_delta=delta,taint=after_health['taint'],no_flash_or_reboot=True,
 only_sensor_module_changed=verified and failure is None,shared_camera_drivers_not_unloaded=True,
 package_database_world_unchanged=all(Path('/'+p).read_bytes()==(root/'backup'/p).read_bytes() for p in ['lib/apk/db/installed','etc/apk/world']))
report['passed']=report['new_module_verified'] and restart_failure is None and report['resources_restored'] and not any(delta.values()) and report['taint']==0
(root/'summary-private.json').write_text(json.dumps(report,indent=2)+'\n')
save('verified' if report['passed'] else 'failed',terminal=True,exit_code=0 if report['passed'] else 1)
print(json.dumps(report))
