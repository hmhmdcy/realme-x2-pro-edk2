from pathlib import Path
import json
import host

code='''from pathlib import Path
import dbus,json,os,subprocess,time
os.umask(0o077)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k189r2-reboot-runtime/boot-id-private.txt').read_bytes()
out=Path('/var/lib/samurai/k190-baseline');assert not out.exists();out.mkdir(mode=0o700)
(out/'boot-id-private.txt').write_bytes(Path('/proc/sys/kernel/random/boot_id').read_bytes())
log=subprocess.check_output(['dmesg'],text=True);(out/'dmesg-private.txt').write_text(log)
bus=dbus.SystemBus(private=True)
manager=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager')
objects=manager.GetManagedObjects()
(out/'modem-objects-private.json').write_text(json.dumps(objects,indent=2,default=str))
modems=[]
for path,interfaces in objects.items():
 if 'org.freedesktop.ModemManager1.Modem' not in interfaces:continue
 p=interfaces['org.freedesktop.ModemManager1.Modem'];location=interfaces.get('org.freedesktop.ModemManager1.Modem.Location')
 modems.append(dict(path=str(path),state=int(p.get('State')),failed_reason=int(p.get('StateFailedReason',0)),plugin=str(p.get('Plugin')),
  location_interface=location is not None,location_properties={str(k):v for k,v in location.items() if k in ['Capabilities','Enabled','SignalsLocation','GpsRefreshRate','SupportedAssistanceData']} if location else {}))
versions={}
for cmd in [['ModemManager','--version'],['qmicli','--version'],['apk','list','--installed','geoclue','gpsd','modemmanager','libqmi']]:
 p=subprocess.run(cmd,capture_output=True);versions[cmd[0]]=p.stdout.decode(errors='replace').strip()
 pth=out/(cmd[0]+'-version-private.txt');pth.write_bytes(p.stdout+p.stderr)
p=subprocess.run(['chronyc','tracking'],capture_output=True);(out/'chrony-private.txt').write_bytes(p.stdout+p.stderr)
report=dict(stage=190,kernel_build=183,same_boot_as189=True,taint=int(Path('/proc/sys/kernel/tainted').read_text()),
 remoteproc={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')},
 current_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),modems=modems,versions=versions,
 chrony_synchronized=b'Leap status     : Normal' in p.stdout,
 fault_counts={k:log.count(v) for k,v in dict(warning='WARNING:',oops='Oops:',gpu='gpu fault:',slpi_fatal='fatal error received',bluetooth='Frame reassembly failed').items()})
bus.close();(out/'summary.json').write_text(json.dumps(report,indent=2,default=str)+'\\n');print(json.dumps(report,default=str))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=45);(host.PRIVATE/'location-baseline-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(Path(__file__).resolve().parent/'location-baseline-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
