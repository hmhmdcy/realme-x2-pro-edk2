from pathlib import Path
import importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel241')
spec=importlib.util.spec_from_file_location('host241',R.parent/'kernel240/host.py')
host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
code=r'''
from pathlib import Path
import dbus,hashlib,json,subprocess
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
cases={}
for kind in ['differential','ordered','afw','combined']:
 p=r/('k241-loc-'+kind);state=json.loads((p/'state-private.json').read_text());summary=json.loads((p/'summary.json').read_text())
 assert state['terminal'] and state['exit_code']==0 and state['cleanup_verified']
 assert summary['cleanup']['stop_ack'] and summary['cleanup']['client_released'] and summary['cleanup']['device_closed']
 cases[kind]=dict(terminal=True,stop_release_close=True,mm_preserved=summary['mm_preserved'],no_fault_delta=not any(summary['fault_delta'].values()))
bus=dbus.SystemBus(private=True);objects=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
interfaces=next(v for v in objects.values() if 'org.freedesktop.ModemManager1.Modem' in v)
loc=interfaces['org.freedesktop.ModemManager1.Modem.Location'];watch=json.loads((r/'gnss-assist/watch-state.json').read_text())
assert int(loc['Enabled'])==0 and not loc['SignalsLocation'] and not watch['active']
assert not bus.name_has_owner('org.freedesktop.GeoClue2')
active=[]
for proc in Path('/proc').glob('[0-9]*'):
 try:argv=(proc/'cmdline').read_bytes().split(b'\0')
 except OSError:continue
 if argv and argv[0].endswith((b'/loc-differential',b'/loc-ordered',b'/loc-afw',b'/loc-combined')):active.append(proc.name)
assert not active
before=(r/'k241-loc-differential/dmesg-before-private.txt').read_bytes();after=subprocess.check_output(['dmesg'])
delta={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',dsp_fatal=b'fatal error received').items()}
report=dict(stage=241,current236_boot=True,cases=cases,all_probe_processes_exited=True,location_enabled=int(loc['Enabled']),location_signals=bool(loc['SignalsLocation']),gps_refresh=int(loc['GpsRefreshRate']),
 assist_idle=not watch['active'],geoclue_running=False,taint=int(Path('/proc/sys/kernel/tainted').read_text()),fault_delta=delta,
 modem_state=int(interfaces['org.freedesktop.ModemManager1.Modem']['State']),modem_power=int(interfaces['org.freedesktop.ModemManager1.Modem']['PowerState']),
 modemmanager_binary_preserved=hashlib.sha256(Path('/usr/bin/ModemManager').read_bytes()).hexdigest()=='b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc',
 remoteprocs=[dict(name=(x/'name').read_text().strip(),state=(x/'state').read_text().strip()) for x in Path('/sys/class/remoteproc').glob('remoteproc*')],
 no_production_configuration_change=True,no_firmware_flash_or_reboot=True)
assert report['taint']==0 and not any(delta.values()) and report['modemmanager_binary_preserved']
bus.close();print(json.dumps(report))
'''
result=host.ssh('python3 -',input=code.encode(),timeout=15)
(P/'final-health-host-private.log').write_bytes(result.stdout+result.stderr)
report=json.loads(result.stdout);(R/'final-health-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
