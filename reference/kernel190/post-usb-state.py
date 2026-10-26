from pathlib import Path
import dbus,hashlib,json,subprocess,tarfile
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k189r2-reboot-runtime/boot-id-private.txt').read_bytes()
root=Path('/var/lib/samurai');out=root/'k190-post-usb';out.mkdir(mode=0o700)
bus=dbus.SystemBus(private=True);service='org.freedesktop.ModemManager1';manager='/org/freedesktop/ModemManager1'
daemon=dbus.Interface(bus.get_object('org.freedesktop.DBus','/org/freedesktop/DBus'),'org.freedesktop.DBus');pid=int(daemon.GetConnectionUnixProcessID(daemon.GetNameOwner(service)))
deployed=json.loads((root/'k190-mm-deploy/summary.json').read_text())
assert hashlib.sha256((Path('/proc')/str(pid)/'exe').read_bytes()).hexdigest()==deployed['installed_sha256']
objects=dbus.Interface(bus.get_object(service,manager),'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
interfaces=next(v for v in objects.values() if 'org.freedesktop.ModemManager1.Modem.Location' in v)
loc=interfaces['org.freedesktop.ModemManager1.Modem.Location'];modem=interfaces['org.freedesktop.ModemManager1.Modem']
log=subprocess.check_output(['dmesg'],text=True);(out/'dmesg-private.txt').write_text(log)
counts={k:log.count(v) for k,v in dict(warning='WARNING:',oops='Oops:',gpu='gpu fault:',slpi_fatal='fatal error received',bluetooth='Frame reassembly failed').items()}
baseline=json.loads((root/'k190-baseline/summary.json').read_text());deltas={k:counts[k]-baseline['fault_counts'][k] for k in counts};assert all(v==0 for v in deltas.values())
sensor=dbus.Interface(bus.get_object('net.hadess.SensorProxy','/net/hadess/SensorProxy'),'org.freedesktop.DBus.Properties').GetAll('net.hadess.SensorProxy')
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')}
report=dict(stage=190,same_boot_as189=True,uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),taint=int(Path('/proc/sys/kernel/tainted').read_text()),
 modemmanager_patched_binary_running=True,supported_assistance_data=int(loc['SupportedAssistanceData']),assistance_servers=len(loc['AssistanceDataServers']),gps_enabled=int(loc['Enabled']),
 modem_state=int(modem['State']),modem_failed_reason=int(modem['StateFailedReason']),bearers=len(modem['Bearers']),remoteprocs=rp,
 sensor_proxy={str(k):bool(v) for k,v in sensor.items() if k in ['HasAccelerometer','HasAmbientLight','HasProximity']},fault_counts=counts,fault_deltas=deltas,
 management_transport='authenticated-wifi',usb_gadget_rebind_performed=True,usb_transport_recovery_proven=False)
assert report['gps_enabled']==0 and report['supported_assistance_data']==1 and report['bearers']==0 and all(v=='running' for v in rp.values())
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');bus.close()
archive=out/'usb-supplement-private.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
 for dirname in ['k190-usb-stall','k190-usb-rebind']:
  tar.add(root/dirname,arcname=dirname)
 tar.add(out/'summary.json',arcname='post-usb-summary.json')
 tar.add(out/'dmesg-private.txt',arcname='post-usb-dmesg-private.txt')
report['supplement_sha256']=hashlib.sha256(archive.read_bytes()).hexdigest()
(out/'summary-with-archive.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
