from pathlib import Path
import dbus,hashlib,json,os,subprocess,tarfile
os.umask(0o077)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k189r2-reboot-runtime/boot-id-private.txt').read_bytes()
root=Path('/var/lib/samurai');out=root/'k191-final';out.mkdir(mode=0o700)
bus=dbus.SystemBus(private=True);service='org.freedesktop.ModemManager1';manager='/org/freedesktop/ModemManager1'
daemon=dbus.Interface(bus.get_object('org.freedesktop.DBus','/org/freedesktop/DBus'),'org.freedesktop.DBus');pid=int(daemon.GetConnectionUnixProcessID(daemon.GetNameOwner(service)))
digest='b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc'
assert hashlib.sha256(Path('/usr/bin/ModemManager').read_bytes()).hexdigest()==digest
assert hashlib.sha256((Path('/proc')/str(pid)/'exe').read_bytes()).hexdigest()==digest
objects=dbus.Interface(bus.get_object(service,manager),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();(out/'modem-objects-private.json').write_text(json.dumps(objects,default=str))
values=next(v for v in objects.values() if service+'.Modem.Location' in v);loc=values[service+'.Modem.Location'];modem=values[service+'.Modem']
assert int(loc['Enabled'])==0 and int(loc['SupportedAssistanceData'])==1 and int(loc['GpsRefreshRate'])==30 and not modem['Bearers']
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')};assert all(v=='running' for v in rp.values())
sensor=dbus.Interface(bus.get_object('net.hadess.SensorProxy','/net/hadess/SensorProxy'),'org.freedesktop.DBus.Properties').GetAll('net.hadess.SensorProxy')
has={str(k):bool(v) for k,v in sensor.items() if k in ['HasAccelerometer','HasAmbientLight','HasProximity']};assert all(has.values())
log=subprocess.check_output(['dmesg'],text=True);(out/'dmesg-private.txt').write_text(log)
baseline=json.loads((root/'k191-baseline/summary.json').read_text())
counts={k:log.count(v) for k,v in dict(warning='WARNING:',oops='Oops:',gpu='gpu fault:',slpi_fatal='fatal error received',bluetooth='Frame reassembly failed').items()};deltas={k:counts[k]-baseline['fault_counts'][k] for k in counts};assert all(v==0 for v in deltas.values())
nv=subprocess.run(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'],capture_output=True);(out/'nv-source-check-private.log').write_bytes(nv.stdout+nv.stderr);assert nv.returncode==0
bt=Path('/etc/bluetooth/main.conf');assert bt.read_bytes()==(root/'k185-policy/main.conf-before-private').read_bytes()
activation=Path('/usr/share/dbus-1/system-services/org.freedesktop.ModemManager1.service');assert activation.read_bytes()==(root/'k191-mm-deploy/original-dbus-service-private').read_bytes()
report=dict(stage=191,same_boot_as189=True,uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),taint=int(Path('/proc/sys/kernel/tainted').read_text()),
 mm191_binary_running=True,supported_assistance_data=int(loc['SupportedAssistanceData']),assistance_servers=len(loc['AssistanceDataServers']),gps_enabled=int(loc['Enabled']),gps_refresh_rate=int(loc['GpsRefreshRate']),
 modem_state=int(modem['State']),modem_failed_reason=int(modem['StateFailedReason']),bearers=len(modem['Bearers']),remoteprocs=rp,sensor_proxy=has,fault_counts=counts,fault_deltas=deltas,
 nv_source_hashes_unchanged=True,bluetooth_policy_unchanged=True,dbus_activation_file_restored=True,management_transport='authenticated-wifi',gps_fix_proven=False)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');bus.close()
archive=out/'evidence-private.tar.gz';files=[]
for directory in sorted(root.glob('k191-*')):
 if directory.is_dir() and directory!=out:files.extend(p for p in directory.rglob('*') if p.is_file() and not p.is_symlink())
files.extend([out/'summary.json',out/'dmesg-private.txt',out/'nv-source-check-private.log',out/'modem-objects-private.json'])
manifest={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files};(out/'manifest-private.json').write_text(json.dumps(manifest,indent=2))
with tarfile.open(archive,'w:gz') as tar:
 for path in files:tar.add(path,arcname=str(path.relative_to(root)),recursive=False)
 tar.add(out/'manifest-private.json',arcname='manifest-private.json')
record=dict(files=len(files),archive_bytes=archive.stat().st_size,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),final=report)
(out/'export-summary.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
