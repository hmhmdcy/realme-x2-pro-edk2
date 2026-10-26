import json
import host

code='''from pathlib import Path
import dbus,json,subprocess
bus=dbus.SystemBus(private=True);api=dbus.Interface(bus.get_object('org.freedesktop.DBus','/org/freedesktop/DBus'),'org.freedesktop.DBus')
report={}
try:owner=api.GetNameOwner('org.freedesktop.ModemManager1')
except dbus.DBusException as error:
 if error.get_dbus_name()!='org.freedesktop.DBus.Error.NameHasNoOwner':raise
 owner=None
report['service_has_owner']=owner is not None
report['process_count']=len(subprocess.run(['pidof','ModemManager'],capture_output=True).stdout.split())
if owner is not None:
 pid=int(api.GetConnectionUnixProcessID(owner));cmd=(Path('/proc')/str(pid)/'cmdline').read_bytes()
 report['debug_log_enabled']=b'--log-level=DEBUG' in cmd
 objects=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
 report['modems']=[]
 for path,items in objects.items():
  if 'org.freedesktop.ModemManager1.Modem.Location' in items:
   m=items['org.freedesktop.ModemManager1.Modem'];l=items['org.freedesktop.ModemManager1.Modem.Location']
   report['modems'].append(dict(path=str(path),state=int(m['State']),failed_reason=int(m['StateFailedReason']),capabilities=int(l['Capabilities']),supported_assistance=int(l['SupportedAssistanceData']),gps_enabled=int(l['Enabled'])))
root=Path('/var/lib/samurai/k190-mm-reinit')
report['activation_original_restored']=Path('/usr/share/dbus-1/system-services/org.freedesktop.ModemManager1.service').read_bytes()==(root/'original-dbus-service-private').read_bytes()
print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode());(host.PRIVATE/'mm-after-reinit-inspection-private.json').write_bytes(p.stdout);print(p.stdout.decode())
