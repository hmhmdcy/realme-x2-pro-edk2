from pathlib import Path
import dbus,hashlib,json,os,subprocess
os.umask(0o077)
out=Path('/var/lib/samurai/k191-baseline');out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k189r2-reboot-runtime/boot-id-private.txt').read_bytes()
expected='fbc4084873e8e79d4bcdfa37982f4016a9e898f7123cecd37ba941ed55f27f69'
assert hashlib.sha256(Path('/usr/bin/ModemManager').read_bytes()).hexdigest()==expected
bus=dbus.SystemBus(private=True);service='org.freedesktop.ModemManager1';manager='/org/freedesktop/ModemManager1'
daemon=dbus.Interface(bus.get_object('org.freedesktop.DBus','/org/freedesktop/DBus'),'org.freedesktop.DBus');pid=int(daemon.GetConnectionUnixProcessID(daemon.GetNameOwner(service)))
assert hashlib.sha256((Path('/proc')/str(pid)/'exe').read_bytes()).hexdigest()==expected
objects=dbus.Interface(bus.get_object(service,manager),'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
values=next(v for v in objects.values() if 'org.freedesktop.ModemManager1.Modem.Location' in v)
loc=values['org.freedesktop.ModemManager1.Modem.Location'];modem=values['org.freedesktop.ModemManager1.Modem']
assert int(loc['Enabled'])==0 and int(loc['SupportedAssistanceData'])==1 and not modem['Bearers']
assert int(modem['State'])==-1 and int(modem['StateFailedReason'])==2
(out/'objects-private.json').write_text(json.dumps(objects,default=str))
log=subprocess.check_output(['dmesg'],text=True);(out/'dmesg-private.txt').write_text(log)
ssc=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  if (p/'exe').resolve()==Path('/usr/libexec/samurai-hexagonrpcd'):ssc.append(int(p.name))
 except FileNotFoundError:pass
assert len(ssc)==1
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')};assert all(v=='running' for v in rp.values())
report=dict(stage=191,same_boot_as189=True,kernel_build=183,taint=int(Path('/proc/sys/kernel/tainted').read_text()),mm190_binary_matches=True,
 supported_assistance_data=int(loc['SupportedAssistanceData']),assistance_servers=len(loc['AssistanceDataServers']),gps_enabled=int(loc['Enabled']),
 modem_state=int(modem['State']),modem_failed_reason=int(modem['StateFailedReason']),bearers=len(modem['Bearers']),remoteprocs=rp,ssc_file_service_processes=len(ssc),
 fault_counts={k:log.count(v) for k,v in dict(warning='WARNING:',oops='Oops:',gpu='gpu fault:',slpi_fatal='fatal error received',bluetooth='Frame reassembly failed').items()})
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');bus.close();print(json.dumps(report))
