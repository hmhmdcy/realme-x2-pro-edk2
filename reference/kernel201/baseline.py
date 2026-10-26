from pathlib import Path
import dbus,hashlib,json,os,subprocess
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k201-baseline';assert not out.exists();out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(root/'k200-runtime/boot-id-private.txt').read_bytes();(out/'boot-id-private.txt').write_bytes(boot)
assert os.uname().version.startswith('#183 ') and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert Path('/sys/firmware/devicetree/base/model').read_bytes()==b'Realme X2 Pro (RMX1931CN)\0'
assert Path('/sys/firmware/devicetree/base/soc@0/camss@acb3000/power-domain-names').read_bytes()==b'ife0\0ife1\0top\0mmcx\0'
assert hashlib.sha256(Path('/usr/bin/ModemManager').read_bytes()).hexdigest()=='b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc'
bus=dbus.SystemBus(private=True);props=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties');m=props.GetAll('org.freedesktop.ModemManager1.Modem');loc=props.GetAll('org.freedesktop.ModemManager1.Modem.Location')
r=dict(stage=201,same_verified_boot200=True,kernel_build=183,taint=0,uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),mm_state=int(m['State']),mm_failed_reason=int(m['StateFailedReason']),mm_power_state=int(m['PowerState']),location_enabled=int(loc['Enabled']),location_capabilities=int(loc['Capabilities']),assistance_data_mask=int(loc['SupportedAssistanceData']),assistance_server_count=len(loc['AssistanceDataServers']))
assert r['location_enabled']==0
sensor=dbus.Interface(bus.get_object('net.hadess.SensorProxy','/net/hadess/SensorProxy'),'org.freedesktop.DBus.Properties');r['sensor_proxy']={n:bool(sensor.Get('net.hadess.SensorProxy',n)) for n in ['HasAccelerometer','HasAmbientLight','HasProximity']};assert all(r['sensor_proxy'].values())
r['geoclue_bus_owned']=bus.name_has_owner('org.freedesktop.GeoClue2');bus.close()
r['remoteprocs']={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')};assert all(v=='running' for v in r['remoteprocs'].values())
log=subprocess.check_output(['dmesg']);(out/'dmesg-private.txt').write_bytes(log);r['fault_counts']={k:log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()};assert not any(r['fault_counts'].values())
for command,name in [(['apk','info','-v','geoclue','geoclue-libs','modemmanager','libqmi'],'packages-private.txt'),(['ps','-eo','uid,pid,comm'],'processes-private.txt')]:
 p=subprocess.run(command,capture_output=True);(out/name).write_bytes(p.stdout+p.stderr)
(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
