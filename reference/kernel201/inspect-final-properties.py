from pathlib import Path
import dbus,json
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k201-baseline/boot-id-private.txt').read_bytes()
bus=dbus.SystemBus(private=True);props=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties');m=props.GetAll('org.freedesktop.ModemManager1.Modem');loc=props.GetAll('org.freedesktop.ModemManager1.Modem.Location')
r=dict(modem={k:int(m[k]) for k in ['State','StateFailedReason','PowerState']},bearers=len(m['Bearers']),location={k:int(loc[k]) for k in ['Enabled','GpsRefreshRate','SignalsLocation']},geoclue_owned=bus.name_has_owner('org.freedesktop.GeoClue2'),watch=json.loads((root/'gnss-assist/watch-state.json').read_text()))
bus.close();print(json.dumps(r))
