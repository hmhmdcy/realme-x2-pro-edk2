import host
code=r'''
from pathlib import Path
import dbus,json
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k204r2-runtime/boot-id-private.txt').read_bytes()
b=dbus.SystemBus(private=True);p=dbus.Interface(b.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties');l=p.GetAll('org.freedesktop.ModemManager1.Modem.Location');m=p.GetAll('org.freedesktop.ModemManager1.Modem');g=b.name_has_owner('org.freedesktop.GeoClue2');inuse=None
if g:inuse=bool(dbus.Interface(b.get_object('org.freedesktop.GeoClue2','/org/freedesktop/GeoClue2/Manager'),'org.freedesktop.DBus.Properties').Get('org.freedesktop.GeoClue2.Manager','InUse'))
print(json.dumps(dict(gps=int(l['Enabled']),signals=bool(l['SignalsLocation']),refresh=int(l['GpsRefreshRate']),power=int(m['PowerState']),bearers=len(m['Bearers']),geoclue_owned=g,geoclue_inuse=inuse)));b.close()
'''
p=host.ssh('python3 -',input=code.encode());(host.PRIVATE/'idle-location-inspection-private.json').write_bytes(p.stdout);print(p.stdout.decode())
