"""One controlled MM reinitialization while SIM/data/GPS are idle; never reset MPSS."""
from pathlib import Path
import configparser,dbus,hashlib,json,os,signal,subprocess,time

os.umask(0o077)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k189r2-reboot-runtime/boot-id-private.txt').read_bytes()
out=Path('/var/lib/samurai/k190-mm-reinit');assert not out.exists();out.mkdir(mode=0o700)
bus=dbus.SystemBus(private=True);manager_path='/org/freedesktop/ModemManager1';service='org.freedesktop.ModemManager1'
objects=dbus.Interface(bus.get_object(service,manager_path),'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
modem='/org/freedesktop/ModemManager1/Modem/0';interfaces=objects[modem]
p=interfaces['org.freedesktop.ModemManager1.Modem'];loc=interfaces['org.freedesktop.ModemManager1.Modem.Location']
assert int(p['State'])==-1 and int(p['StateFailedReason'])==2 and not p['Bearers'] and int(loc['Enabled'])==0
(out/'objects-before-private.json').write_text(json.dumps(objects,indent=2,default=str))
dbus_api=dbus.Interface(bus.get_object('org.freedesktop.DBus','/org/freedesktop/DBus'),'org.freedesktop.DBus')
owner=dbus_api.GetNameOwner(service);pid=int(dbus_api.GetConnectionUnixProcessID(owner))
exe=(Path('/proc')/str(pid)/'exe').resolve();assert exe==Path('/usr/bin/ModemManager')
args=(Path('/proc')/str(pid)/'cmdline').read_bytes().split(b'\0')[:-1];assert len(args)==1
(out/'original-command-private.json').write_text(json.dumps([os.fsdecode(a) for a in args]))
activation=Path('/usr/share/dbus-1/system-services/org.freedesktop.ModemManager1.service')
original=activation.read_bytes();(out/'original-dbus-service-private').write_bytes(original)
lines=original.decode().splitlines();assert sum(line.startswith('Exec=') for line in lines)==1
log=out/'daemon-debug-private.log';debug_args=[str(exe),'--log-level=DEBUG','--log-file='+str(log)]
text='\n'.join('Exec='+' '.join(debug_args) if line.startswith('Exec=') else line for line in lines)+'\n'
temporary=activation.with_name(activation.name+'.k190');temporary.write_text(text);temporary.chmod(activation.stat().st_mode&0o777);temporary.replace(activation)
report=dict(stage=190,old_state_failed_sim_missing=True,bearers_before=0,gps_before_enabled=0,modem_remoteproc_reset=False)
child=None
try:
 os.kill(pid,signal.SIGTERM)
 deadline=time.monotonic()+15
 while dbus_api.NameHasOwner(service) and dbus_api.GetNameOwner(service)==owner and time.monotonic()<deadline:time.sleep(.1)
 assert not dbus_api.NameHasOwner(service) or dbus_api.GetNameOwner(service)!=owner
 if not dbus_api.NameHasOwner(service):
  with (out/'launcher-private.log').open('wb') as stream:child=subprocess.Popen(debug_args,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
 deadline=time.monotonic()+100;record=None
 while time.monotonic()<deadline:
  if dbus_api.NameHasOwner(service):
   current_owner=dbus_api.GetNameOwner(service);new_pid=int(dbus_api.GetConnectionUnixProcessID(current_owner))
   cmd=(Path('/proc')/str(new_pid)/'cmdline').read_bytes()
   assert b'--log-level=DEBUG' in cmd and os.fsencode(log) in cmd
   objects=dbus.Interface(bus.get_object(service,manager_path),'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
   for path,values in objects.items():
    if 'org.freedesktop.ModemManager1.Modem.Location' in values and int(values['org.freedesktop.ModemManager1.Modem']['State'])==-1:
     mp=values['org.freedesktop.ModemManager1.Modem'];lp=values['org.freedesktop.ModemManager1.Modem.Location']
     record=dict(state=int(mp['State']),failed_reason=int(mp['StateFailedReason']),location_capabilities=int(lp['Capabilities']),supported_assistance_data=int(lp['SupportedAssistanceData']),gps_enabled=int(lp['Enabled']))
   if record is not None:break
  time.sleep(.5)
 assert record is not None
 report.update(new_owner_verified=True,after=record)
 (out/'new-daemon-pid-private.txt').write_text(str(new_pid)+'\n')
finally:
 restore=activation.with_name(activation.name+'.k190-restore');restore.write_bytes(original);restore.chmod(activation.stat().st_mode&0o777);restore.replace(activation)
 assert activation.read_bytes()==original
 report['dbus_activation_file_restored']=True
 (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
 bus.close()
print(json.dumps(report))
