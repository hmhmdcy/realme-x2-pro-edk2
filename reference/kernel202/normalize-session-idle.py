from pathlib import Path
import dbus,json,time
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k202-runtime/boot-id-private.txt').read_bytes()
bus=dbus.SystemBus(private=True);obj=bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0');props=dbus.Interface(obj,'org.freedesktop.DBus.Properties');api=dbus.Interface(obj,'org.freedesktop.ModemManager1.Modem.Location')
assert not bus.name_has_owner('org.freedesktop.GeoClue2') and int(props.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'))==0
before=props.GetAll('org.freedesktop.ModemManager1.Modem.Location');api.Setup(dbus.UInt32(0),dbus.Boolean(False),timeout=20);api.SetGpsRefreshRate(dbus.UInt32(30),timeout=10);time.sleep(4)
after=props.GetAll('org.freedesktop.ModemManager1.Modem.Location');assert int(after['Enabled'])==0 and not after['SignalsLocation'] and int(after['GpsRefreshRate'])==30 and not bus.name_has_owner('org.freedesktop.GeoClue2')
r=dict(stage=202,gps_remained_disabled=True,previous_signals_location=bool(before['SignalsLocation']),previous_refresh_rate=int(before['GpsRefreshRate']),final_signals_location=False,final_refresh_rate=30,geoclue_bus_unowned=True,delayed_property_change_cause_not_established=True)
(root/'k202-helper-deploy/idle-normalization.json').write_text(json.dumps(r,indent=2)+'\n');bus.close();print(json.dumps(r))
