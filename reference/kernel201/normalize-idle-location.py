from pathlib import Path
import dbus,json,time
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k201-baseline/boot-id-private.txt').read_bytes()
out=root/'k201-idle-normalization';assert not out.exists();out.mkdir(mode=0o700)
bus=dbus.SystemBus(private=True);assert not bus.name_has_owner('org.freedesktop.GeoClue2')
obj=bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0');props=dbus.Interface(obj,'org.freedesktop.DBus.Properties');api=dbus.Interface(obj,'org.freedesktop.ModemManager1.Modem.Location')
before=props.GetAll('org.freedesktop.ModemManager1.Modem.Location');assert int(before['Enabled'])==0
watch=json.loads((root/'gnss-assist/watch-state.json').read_text());assert not watch['active'] and watch['worker_starts']==watch['worker_completions']
api.Setup(dbus.UInt32(0),dbus.Boolean(False),timeout=25);api.SetGpsRefreshRate(dbus.UInt32(30),timeout=10);time.sleep(1)
after=props.GetAll('org.freedesktop.ModemManager1.Modem.Location');assert int(after['Enabled'])==0 and not after['SignalsLocation'] and int(after['GpsRefreshRate'])==30
r=dict(stage=201,normalization_after_isolated_tests=True,pre_normalization_refresh_and_signal_settings_recorded=True,before={k:int(before[k]) for k in ['Enabled','SignalsLocation','GpsRefreshRate']},after={k:int(after[k]) for k in ['Enabled','SignalsLocation','GpsRefreshRate']},gps_engine_not_started=True,modem_power_state_unchanged=int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState')))
(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');bus.close();print(json.dumps(r))
