"""Replace only the MM executable, with an automatic byte-for-byte rollback."""
from pathlib import Path
import dbus,hashlib,json,os,signal,subprocess,time
os.umask(0o077)
def boot():
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k189r2-reboot-runtime/boot-id-private.txt').read_bytes()
boot()
out=Path('/var/lib/samurai/k190-mm-deploy');out.mkdir(mode=0o700)
build=Path('/var/lib/samurai/k190-mm-build');validation=json.loads((build/'candidate-validation.json').read_text())
candidate=build/'candidate/ModemManager';new=candidate.read_bytes();assert hashlib.sha256(new).hexdigest()==validation['deployable_sha256']
exe=Path('/usr/bin/ModemManager');old=exe.read_bytes();mode=exe.stat().st_mode&0o777
(out/'ModemManager.original').write_bytes(old);(out/'ModemManager.original').chmod(mode)
db=Path('/lib/apk/db/installed').read_bytes()
bus=dbus.SystemBus(private=True);service='org.freedesktop.ModemManager1';manager='/org/freedesktop/ModemManager1'
daemon=dbus.Interface(bus.get_object('org.freedesktop.DBus','/org/freedesktop/DBus'),'org.freedesktop.DBus')
def owner_now():
 try:return daemon.GetNameOwner(service)
 except dbus.DBusException as e:
  if e.get_dbus_name()=='org.freedesktop.DBus.Error.NameHasNoOwner':return None
  raise
def objects():return dbus.Interface(bus.get_object(service,manager),'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
def record(values):
 modem=values['org.freedesktop.ModemManager1.Modem'];loc=values['org.freedesktop.ModemManager1.Modem.Location']
 return dict(state=int(modem['State']),failed_reason=int(modem['StateFailedReason']),bearers=len(modem['Bearers']),location_capabilities=int(loc['Capabilities']),supported_assistance_data=int(loc['SupportedAssistanceData']),assistance_servers=len(loc['AssistanceDataServers']),gps_enabled=int(loc['Enabled']))
before_objects=objects();assert len([v for v in before_objects.values() if 'org.freedesktop.ModemManager1.Modem' in v])==1
before=record(next(v for v in before_objects.values() if 'org.freedesktop.ModemManager1.Modem.Location' in v))
assert before['state']==-1 and before['failed_reason']==2 and before['bearers']==0 and before['gps_enabled']==0 and before['supported_assistance_data']==0
(out/'objects-before-private.json').write_text(json.dumps(before_objects,default=str))
old_owner=owner_now();old_pid=int(daemon.GetConnectionUnixProcessID(old_owner));proc=Path('/proc')/str(old_pid)
assert (proc/'exe').resolve()==exe
args=(proc/'cmdline').read_bytes();assert b'k190-mm-reinit-r2/daemon-debug-private.log' in args
(out/'command-before-private.bin').write_bytes(args)
activation=Path('/usr/share/dbus-1/system-services/org.freedesktop.ModemManager1.service');original_activation=activation.read_bytes()
assert original_activation==Path('/var/lib/samurai/k190-mm-reinit-r2/original-dbus-service-private').read_bytes()
(out/'original-dbus-service-private').write_bytes(original_activation)
rp={p.name:(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')}
assert all(v=='running' for v in rp.values())
def replace(path,data,permissions):
 temp=path.with_name(path.name+'.k190-new');assert not temp.exists();temp.write_bytes(data);temp.chmod(permissions)
 with temp.open('rb') as stream:os.fsync(stream.fileno())
 temp.replace(path)
def stop_verified(owner,pid,expected):
 boot();assert owner_now()==owner and int(daemon.GetConnectionUnixProcessID(owner))==pid
 assert hashlib.sha256((Path('/proc')/str(pid)/'exe').read_bytes()).hexdigest()==expected
 os.kill(pid,signal.SIGTERM)
 deadline=time.monotonic()+20
 while owner_now()==owner and time.monotonic()<deadline:time.sleep(.1)
 assert owner_now()!=owner
report=dict(stage=190,before=before,original_sha256=hashlib.sha256(old).hexdigest(),installed_sha256=hashlib.sha256(new).hexdigest(),modem_remoteproc_reset=False,success=False)
installed=False;activation_changed=False
try:
 replace(exe,new,mode);installed=True
 log=out/'daemon-debug-private.log'
 lines=original_activation.decode().splitlines();assert sum(line.startswith('Exec=') for line in lines)==1
 text='\n'.join('Exec=/usr/bin/ModemManager --log-level=DEBUG --log-file='+str(log) if line.startswith('Exec=') else line for line in lines)+'\n'
 replace(activation,text.encode(),activation.stat().st_mode&0o777);activation_changed=True;daemon.ReloadConfig()
 stop_verified(old_owner,old_pid,report['original_sha256'])
 if owner_now() is None:
  # Ask the bus to use the reviewed activation command, so subsequent launches
  # keep the usual ownership and activation semantics.
  daemon.StartServiceByName(service,dbus.UInt32(0),timeout=30)
 deadline=time.monotonic()+100;after=None
 while time.monotonic()<deadline:
  owner=owner_now()
  if owner is not None:
   pid=int(daemon.GetConnectionUnixProcessID(owner));p=Path('/proc')/str(pid)
   assert hashlib.sha256((p/'exe').read_bytes()).hexdigest()==report['installed_sha256']
   values=objects()
   for path,interfaces in values.items():
    if 'org.freedesktop.ModemManager1.Modem.Location' in interfaces:
     r=record(interfaces)
     if r['state']==-1:
      after=r;break
   if after is not None:break
  time.sleep(.25)
 assert after is not None
 assert after['state']==-1 and after['failed_reason']==2 and after['bearers']==0 and after['gps_enabled']==0
 assert after['supported_assistance_data']==1 and after['assistance_servers']>0
 assert {p.name:(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')}==rp
 assert Path('/lib/apk/db/installed').read_bytes()==db
 (out/'objects-after-private.json').write_text(json.dumps(values,default=str))
 (out/'new-daemon-pid-private.txt').write_text(str(pid)+'\n')
 dbus.Interface(bus.get_object(service,manager),service).SetLogging('INFO')
 report.update(after=after,success=True,new_binary_running=True,logging_restored_to_info=True,package_database_unchanged=True,remoteprocs_running_unchanged=True)
except BaseException as error:
 report['error_type']=type(error).__name__
 (out/'failure-private.txt').write_text(str(error))
 if installed:
  replace(exe,old,mode);report['original_binary_restored']=exe.read_bytes()==old
  owner=owner_now()
  if owner is not None:
   pid=int(daemon.GetConnectionUnixProcessID(owner))
   if hashlib.sha256((Path('/proc')/str(pid)/'exe').read_bytes()).hexdigest()==report['installed_sha256']:
    stop_verified(owner,pid,report['installed_sha256'])
finally:
 if activation_changed:replace(activation,original_activation,activation.stat().st_mode&0o777);daemon.ReloadConfig()
 report['dbus_activation_file_restored']=activation.read_bytes()==original_activation
 if not report['success'] and owner_now() is None:daemon.StartServiceByName(service,dbus.UInt32(0),timeout=30)
 (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');bus.close()
print(json.dumps(report))
assert report['success']
