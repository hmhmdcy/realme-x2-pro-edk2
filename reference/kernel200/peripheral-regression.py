from pathlib import Path
import dbus,json,subprocess,time

root=Path('/var/lib/samurai');out=root/'k200-peripheral-regression';assert not out.exists();out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k200-runtime/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
before=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(before)
bus=dbus.SystemBus(private=True);report=dict(stage=200,bluetooth_scan_only=True,no_pair_connect_or_haptic_commands=True)
props=dbus.Interface(bus.get_object('net.hadess.SensorProxy','/net/hadess/SensorProxy'),'org.freedesktop.DBus.Properties')
report['sensor_proxy']={n:bool(props.Get('net.hadess.SensorProxy',n)) for n in ['HasAccelerometer','HasAmbientLight','HasProximity']};assert all(report['sensor_proxy'].values())
sensor=dbus.Interface(bus.get_object('net.hadess.SensorProxy','/net/hadess/SensorProxy'),'net.hadess.SensorProxy');claims=[]
try:
 for name in ['Accelerometer','Light','Proximity']:
  getattr(sensor,'Claim'+name)(timeout=10);claims.append(name)
 time.sleep(5)
 values=props.GetAll('net.hadess.SensorProxy');(out/'sensor-properties-private.json').write_text(json.dumps(dict(values),default=str))
finally:
 for name in reversed(claims):getattr(sensor,'Release'+name)(timeout=10)
report['sensor_claims_released']=claims
objects=dbus.Interface(bus.get_object('org.bluez','/'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
adapters=[p for p,i in objects.items() if 'org.bluez.Adapter1' in i];assert len(adapters)==1
obj=bus.get_object('org.bluez',adapters[0]);adapter=dbus.Interface(obj,'org.bluez.Adapter1');ap=dbus.Interface(obj,'org.freedesktop.DBus.Properties')
powered=bool(ap.Get('org.bluez.Adapter1','Powered'));discovering=bool(ap.Get('org.bluez.Adapter1','Discovering'));assert not discovering
started=False
try:
 if not powered:ap.Set('org.bluez.Adapter1','Powered',dbus.Boolean(True),timeout=15)
 adapter.StartDiscovery(timeout=15);started=True
 assert ap.Get('org.bluez.Adapter1','Discovering');time.sleep(8)
 objects=dbus.Interface(bus.get_object('org.bluez','/'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
 (out/'bluetooth-objects-private.json').write_text(json.dumps(dict(objects),default=str))
 report['bluetooth_scan_seconds']=8;report['bluetooth_discovered_device_count']=sum('org.bluez.Device1' in i for i in objects.values())
finally:
 if started:adapter.StopDiscovery(timeout=10)
 if not powered:ap.Set('org.bluez.Adapter1','Powered',dbus.Boolean(False),timeout=10)
report['bluetooth_discovery_stopped']=not bool(ap.Get('org.bluez.Adapter1','Discovering'));report['bluetooth_power_state_restored']=bool(ap.Get('org.bluez.Adapter1','Powered'))==powered
mp=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties')
m=mp.GetAll('org.freedesktop.ModemManager1.Modem');loc=mp.GetAll('org.freedesktop.ModemManager1.Modem.Location')
report['modem']=dict(state=int(m['State']),power=int(m['PowerState']),location_enabled=int(loc['Enabled']),supported_location_sources=int(loc['Capabilities']),assistance_data_mask=int(loc.get('SupportedAssistanceData',0)),assistance_server_count=len(loc.get('AssistanceDataServers',[])),real_registration_or_gnss_fix_not_validated=True)
bus.close()
report['remoteprocs']={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')}
after=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(after)
report['fault_delta']={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()}
report['taint']=int(Path('/proc/sys/kernel/tainted').read_text());(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
