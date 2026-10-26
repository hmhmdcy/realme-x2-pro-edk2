import host

native=r'''
from pathlib import Path
import dbus,json,os
root=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k207r2-runtime/boot-id-private.txt').read_bytes()
out=root/'k207r2-late-location';out.mkdir(mode=0o700)
bus=dbus.SystemBus(private=True)
props=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties')
loc=props.GetAll('org.freedesktop.ModemManager1.Modem.Location')
owned=bus.name_has_owner('org.freedesktop.GeoClue2')
geo={}
if owned:
    manager=bus.get_object('org.freedesktop.GeoClue2','/org/freedesktop/GeoClue2/Manager')
    geo=dbus.Interface(manager,'org.freedesktop.DBus.Properties').GetAll('org.freedesktop.GeoClue2.Manager')
    (out/'geoclue-manager-private.json').write_text(json.dumps(geo,default=str,indent=2)+'\n')
    (out/'geoclue-manager-introspect-private.xml').write_text(dbus.Interface(manager,'org.freedesktop.DBus.Introspectable').Introspect())
watch=json.loads((root/'gnss-assist/watch-state.json').read_text())
report=dict(stage=207,gps_enabled=int(loc['Enabled']),signals_location=bool(loc['SignalsLocation']),gps_refresh_rate=int(loc['GpsRefreshRate']),geoclue_owned=owned,geoclue_in_use=bool(geo.get('InUse',False)),worker_starts=watch['worker_starts'],worker_completions=watch['worker_completions'],watch_active=watch['active'],uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]))
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
bus.close()
print(json.dumps(report))
'''
failure=host.PRIVATE/'transport-last-failure-private.log'
saved=host.PRIVATE/'first-final-health-failure-private.log'
if failure.exists() and not saved.exists():saved.write_bytes(failure.read_bytes())
p=host.ssh('python3 -',input=native.encode(),timeout=30)
(host.PRIVATE/'late-location-inspection-private.json').write_bytes(p.stdout)
print(p.stdout.decode())
