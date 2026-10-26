"""Collect public engineering results only; all raw modem/location logs stay private."""
from pathlib import Path
import json,subprocess
import host
code=b'''from pathlib import Path
import dbus,hashlib,json,re,subprocess,time
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k189r2-reboot-runtime/boot-id-private.txt').read_bytes()
root=Path('/var/lib/samurai');out=root/'k190-final';out.mkdir(mode=0o700)
bus=dbus.SystemBus(private=True);service='org.freedesktop.ModemManager1';base='/org/freedesktop/ModemManager1'
daemon=dbus.Interface(bus.get_object('org.freedesktop.DBus','/org/freedesktop/DBus'),'org.freedesktop.DBus')
owner=daemon.GetNameOwner(service);pid=int(daemon.GetConnectionUnixProcessID(owner));exe=Path('/proc')/str(pid)/'exe'
deploy=json.loads((root/'k190-mm-deploy/summary.json').read_text());assert hashlib.sha256(exe.read_bytes()).hexdigest()==deploy['installed_sha256']
objects=dbus.Interface(bus.get_object(service,base),'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
values=next(v for v in objects.values() if 'org.freedesktop.ModemManager1.Modem.Location' in v)
loc=values['org.freedesktop.ModemManager1.Modem.Location'];assert int(loc['Enabled'])==0 and int(loc['SupportedAssistanceData'])==1
lines=(root/'k190-mm-deploy/daemon-debug-private.log').read_text().splitlines()
packets=[]
for i,line in enumerate(lines):
 if 'message     = "Get Predicted Orbits Data Source"' not in line:continue
 flags=None;transaction=None
 for field in lines[max(0,i-12):i]:
  f=re.search(r'flags\\s+= "(none|response|indication)"',field)
  t=re.search(r'transaction = (\\d+)',field)
  if f:flags=f[1]
  if t:transaction=int(t[1])
 packets.append(dict(type=flags,transaction=transaction))
assert [p['type'] for p in packets]==['none','indication','response']
assert len({p['transaction'] for p in packets})==1
baseline=json.loads((root/'k190-baseline/summary.json').read_text())
log=subprocess.check_output(['dmesg'],text=True);(out/'dmesg-private.txt').write_text(log)
counts={k:log.count(v) for k,v in dict(warning='WARNING:',oops='Oops:',gpu='gpu fault:',slpi_fatal='fatal error received',bluetooth='Frame reassembly failed').items()}
deltas={k:counts[k]-baseline['fault_counts'][k] for k in counts};assert all(v==0 for v in deltas.values())
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')}
assert all(v=='running' for v in rp.values())
sensor=dbus.Interface(bus.get_object('net.hadess.SensorProxy','/net/hadess/SensorProxy'),'org.freedesktop.DBus.Properties').GetAll('net.hadess.SensorProxy')
has={str(k):bool(v) for k,v in sensor.items() if k in ['HasAccelerometer','HasAmbientLight','HasProximity']};assert has and all(has.values())
report=dict(stage=190,same_boot_as189=True,kernel_build=183,taint=int(Path('/proc/sys/kernel/tainted').read_text()),
 mm_executable_matches_deployed=True,mm_early_indication_order=packets,early_indication_handled_on_device=True,
 supported_assistance_data=int(loc['SupportedAssistanceData']),assistance_servers=len(loc['AssistanceDataServers']),gps_enabled=int(loc['Enabled']),
 gps_refresh_rate=int(loc['GpsRefreshRate']),remoteprocs=rp,sensor_proxy=has,fault_counts=counts,fault_deltas=deltas,
 standalone_gps_fix_proven=False,orbit_data_injection_proven=False)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\\n');bus.close();print(json.dumps(report))
'''
try:p=host.ssh('python3 -',input=code,timeout=60)
except subprocess.CalledProcessError as e:
 (host.PRIVATE/'collect-mm-result-failure-private.log').write_bytes(e.stdout+e.stderr);raise SystemExit('Final collection failed; private logs retained')
report=json.loads(p.stdout);ref=Path(__file__).resolve().parent
(ref/'mm-native-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
for name,src in [('mm-build-validation.json','k190-mm-build/build-validation.json'),('mm-candidate-validation.json','k190-mm-build/candidate-validation.json'),('mm-deployment-validation.json','k190-mm-deploy/summary.json')]:
 dest=host.PRIVATE/name;host.download('/var/lib/samurai/'+src,dest)
 record=json.loads(dest.read_text());(ref/name).write_text(json.dumps(record,indent=2)+'\n')
