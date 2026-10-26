from pathlib import Path
import dbus,hashlib,json,os,subprocess,time
os.umask(0o077)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k189r2-reboot-runtime/boot-id-private.txt').read_bytes()
out=Path('/var/lib/samurai/k191-assistance');assert (out/'xtra-private.bin').is_file() and not (out/'summary.json').exists()
data=(out/'xtra-private.bin').read_bytes();assert hashlib.sha256(data).hexdigest()=='e905a7291990c20324210b3bb405d84f8088da283f969255e2b28e34676d4008'
bus=dbus.SystemBus(private=True);service='org.freedesktop.ModemManager1';manager='/org/freedesktop/ModemManager1'
daemon=dbus.Interface(bus.get_object('org.freedesktop.DBus','/org/freedesktop/DBus'),'org.freedesktop.DBus')
owner=daemon.GetNameOwner(service);pid=int(daemon.GetConnectionUnixProcessID(owner))
assert hashlib.sha256((Path('/proc')/str(pid)/'exe').read_bytes()).hexdigest()=='b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc'
obj=bus.get_object(service,'/org/freedesktop/ModemManager1/Modem/0');props=dbus.Interface(obj,'org.freedesktop.DBus.Properties')
loc=props.GetAll(service+'.Modem.Location');modem=props.GetAll(service+'.Modem')
assert int(loc['Enabled'])==0 and int(loc['SupportedAssistanceData'])==1 and not modem['Bearers']
assert int(modem['State'])==-1 and int(modem['StateFailedReason'])==2
api=dbus.Interface(obj,service+'.Modem.Location');control=dbus.Interface(bus.get_object(service,manager),service)
log_before=subprocess.check_output(['dmesg'],text=True);(out/'dmesg-before-private.txt').write_text(log_before)
report=dict(stage=191,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),standard_mm_dbus_method=True,injection_ack=False,engine_start_sent=False)
start=time.monotonic()
try:
 control.SetLogging('DEBUG')
 api.InjectAssistanceData(dbus.ByteArray(data),timeout=120);report['injection_ack']=True
except dbus.DBusException as error:
 report['error_name']=error.get_dbus_name();(out/'error-private.txt').write_text(str(error))
finally:
 control.SetLogging('INFO');report['logging_restored_to_info']=True
 report['elapsed_seconds']=time.monotonic()-start
 report['same_mm_owner']=daemon.GetNameOwner(service)==owner
 report['gps_enabled_final']=int(props.Get(service+'.Modem.Location','Enabled'))
 log_after=subprocess.check_output(['dmesg'],text=True);(out/'dmesg-after-private.txt').write_text(log_after)
 report['fault_delta']={k:log_after.count(v)-log_before.count(v) for k,v in dict(warning='WARNING:',oops='Oops:',gpu='gpu fault:',slpi_fatal='fatal error received',modem_fatal='crash detected in modem').items()}
 (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');bus.close()
print(json.dumps(report))
assert report['injection_ack'] and report['same_mm_owner'] and report['gps_enabled_final']==0 and all(v==0 for v in report['fault_delta'].values())
