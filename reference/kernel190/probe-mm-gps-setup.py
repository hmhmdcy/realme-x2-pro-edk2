"""Exercise standard GPS setup without altering SIM/modem operating mode."""
from pathlib import Path
import json
import host

code='''from pathlib import Path
import dbus,json,subprocess,os
os.umask(0o077)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k189r2-reboot-runtime/boot-id-private.txt').read_bytes()
root=Path('/var/lib/samurai/k190-mm-gps-setup');assert not root.exists();root.mkdir(mode=0o700)
bus=dbus.SystemBus(private=True)
obj=bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0')
props=dbus.Interface(obj,'org.freedesktop.DBus.Properties')
before=props.GetAll('org.freedesktop.ModemManager1.Modem.Location');assert int(before['Enabled'])==0
api=dbus.Interface(obj,'org.freedesktop.ModemManager1.Modem.Location')
report=dict(stage=190,before_enabled=0,requested_sources=6,setup_success=False)
try:
 api.Setup(dbus.UInt32(6),dbus.Boolean(False),timeout=45)
 report['setup_success']=True
except dbus.DBusException as error:
 report.update(error_name=error.get_dbus_name(),error_message=str(error))
finally:
 after=props.GetAll('org.freedesktop.ModemManager1.Modem.Location')
 report['after_enabled']=int(after['Enabled'])
 if int(after['Enabled'])!=0:
  api.Setup(dbus.UInt32(0),dbus.Boolean(False),timeout=30)
  report['cleanup_disable_ack']=True
 report['final_enabled']=int(props.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'))
 bus.close()
 (root/'summary.json').write_text(json.dumps(report,indent=2)+'\\n');print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=95);(host.PRIVATE/'mm-setup-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(Path(__file__).resolve().parent/'mm-gps-setup-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
