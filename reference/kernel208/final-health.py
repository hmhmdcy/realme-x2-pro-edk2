from pathlib import Path
import dbus,hashlib,json,os,runpy,subprocess,sys,time
sys.path.insert(0,'/var/lib/samurai/k208-loc-tools')
from loc_nmea import LocSession
os.umask(0o077)
root=Path('/var/lib/samurai');boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot==(root/'k208-baseline/boot-id-private.txt').read_bytes()
out=root/'k208-final-health';out.mkdir(mode=0o700)
(out/'boot-id-private.txt').write_bytes(boot)
for name in ['k208-debug-nmea','k208-debug-nmea-r2']:
    value=json.loads((root/name/'summary.json').read_text())
    assert value['nmea_mask_restored'] and value['gps_enabled_final']==0 and value['client_released'] and value['device_closed']
bus=dbus.SystemBus(private=True)
obj=bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0')
props=dbus.Interface(obj,'org.freedesktop.DBus.Properties');api=dbus.Interface(obj,'org.freedesktop.ModemManager1.Modem.Location')
loc=props.GetAll('org.freedesktop.ModemManager1.Modem.Location')
assert int(loc['Enabled'])==0 and not bus.name_has_owner('org.freedesktop.GeoClue2')
late=dict(signals_location=bool(loc['SignalsLocation']),gps_refresh_rate=int(loc['GpsRefreshRate']))
(out/'idle-location-before-private.json').write_text(json.dumps(late,indent=2)+'\n')
normalized=late!=dict(signals_location=False,gps_refresh_rate=30)
if normalized:
    api.Setup(dbus.UInt32(0),dbus.Boolean(False),timeout=25);api.SetGpsRefreshRate(dbus.UInt32(30),timeout=10)
loc=props.GetAll('org.freedesktop.ModemManager1.Modem.Location')
assert not loc['SignalsLocation'] and int(loc['GpsRefreshRate'])==30
modem=props.GetAll('org.freedesktop.ModemManager1.Modem')
objects=dbus.Interface(bus.get_object('org.bluez','/'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
adapters=[v['org.bluez.Adapter1'] for v in objects.values() if 'org.bluez.Adapter1' in v]
assert len(adapters)==1 and not adapters[0]['Powered'] and not adapters[0]['Discovering']
assert not any(v.get('org.bluez.Device1',{}).get('Connected',False) for v in objects.values())
bus.close()
session=LocSession()
try:session.open();mask=session.nmea_mask();assert mask==63
finally:closed=session.close()
assert closed['client_released'] and closed['device_closed']
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
expected={'/usr/bin/ModemManager':'b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc','/usr/sbin/samurai-gnss-assist':'42168f33472d01dbf115ea766487c70d95332aabc8de02c25bdb381cea80af97','/usr/sbin/samurai-tqftpserv':'b3bb82b9d090a5d06e9ba2ca24e3373ab1c1e7cc2a5c6b603e2acb02715487a1','/usr/sbin/samurai-wifi':'854c9a8c787d68ccefc998064983f3aa67141fe94def27f4dde87925bd18f24f','/usr/sbin/samurai-modem-configs':'d4c62be6054b3ff74f3ed2868c4b456ccb519f75954ad7094235826559a64862'}
assert all(sha(path)==digest for path,digest in expected.items())
assert sha(Path('/usr/lib/modules')/os.uname().release/'kernel/drivers/bluetooth/hci_uart.ko')=='f6c5ed3538270480a72cf4bf8b1339103417941930b0d8ecb941fd11d16d7020'
pid=int(Path('/run/samurai-wifi/tftp.pid').read_text());assert sha('/proc/%d/exe'%pid)==expected['/usr/sbin/samurai-tqftpserv']
check=subprocess.run(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'],capture_output=True)
(out/'nv-check-private.txt').write_bytes(check.stdout+check.stderr);assert check.returncode==0
watch=json.loads((root/'gnss-assist/watch-state.json').read_text())
(out/'watch-private.json').write_text(json.dumps(watch,indent=2)+'\n')
assert watch['running'] and not watch['active'] and watch['worker_starts']==watch['worker_completions']==2
helper=runpy.run_path('/usr/sbin/samurai-gnss-assist',run_name='readonly208')
validity=helper['loc_exchange']('validity');assert helper['validity_current'](validity['start'],validity['hours'],time.time())
(out/'validity-private.json').write_text(json.dumps(validity,indent=2)+'\n')
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')}
assert len(rp)==3 and all(value=='running' for value in rp.values())
log=subprocess.check_output(['dmesg']);(out/'dmesg-private.txt').write_bytes(log)
faults={k:log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()}
assert not any(faults.values()) and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert boot==Path('/proc/sys/kernel/random/boot_id').read_bytes()
report=dict(stage=208,same207_second_boot_verified=True,rebooted=False,partitions_flashed=[],nmea_mask_independently_verified=mask,gnss_enabled=0,idle_location_before=late,late_idle_location_normalized=normalized,signals_location=False,gps_refresh_rate=30,bt_powered=False,bt_connections=0,production_binaries_and_bt185_unchanged=True,nv_sources_unchanged=True,worker_starts=watch['worker_starts'],worker_completions=watch['worker_completions'],assistance_current=True,assistance_hours=validity['hours'],remoteprocs=rp,taint=0,fault_counts=faults,modem_power_state=int(modem['PowerState']),modem_state=int(modem['State']),uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]))
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
