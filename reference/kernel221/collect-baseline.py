from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import dbus,hashlib,json,os,subprocess
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k221-baseline'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k220-baseline/boot-id-private.txt').read_bytes()
assert Path('/sys/firmware/devicetree/base/model').read_bytes()==b'Realme X2 Pro (RMX1931CN)\0' and os.uname().version.startswith('#183 ')
assert not out.exists();out.mkdir(mode=0o700)
(out/'boot-id-private.txt').write_bytes(Path('/proc/sys/kernel/random/boot_id').read_bytes())
module=Path('/usr/lib/modules')/os.uname().release/'kernel/drivers/media/i2c/imx471.ko'
assert hashlib.sha256(module.read_bytes()).hexdigest()=='e49dab26b05a325df8da64bb5c4b57c29cd51d1dcf15f5d4ed4dcb53033e66f1'
assert Path('/sys/module/imx471/parameters/unprocessed_fullres').read_text().strip()=='N'
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
bus=dbus.SystemBus(private=True)
manager=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager')
objects=manager.GetManagedObjects();modems=[(p,i) for p,i in objects.items() if 'org.freedesktop.ModemManager1.Modem' in i];assert len(modems)==1
path,interfaces=modems[0];modem=interfaces['org.freedesktop.ModemManager1.Modem'];location=interfaces['org.freedesktop.ModemManager1.Modem.Location']
(out/'modem-path-private.txt').write_text(str(path))
gps=dict(enabled=int(location['Enabled']),signals=bool(location['SignalsLocation']),rate=int(location['GpsRefreshRate']))
assert gps==dict(enabled=0,signals=False,rate=30)
sim=modem.get('Sim',dbus.ObjectPath('/'));sim_object_present=sim!='/' and sim in objects
properties={k:int(modem[k]) for k in ['State','StateFailedReason','PowerState','UnlockRequired']}
properties.update(sim_path_present=sim!='/',sim_object_present=sim_object_present,bearer_count=len(modem.get('Bearers',[])))
bus.close()
queries={}
for option in ['dms-get-operating-mode','loc-get-operation-mode','loc-get-engine-lock','loc-get-nmea-types']:
 p=subprocess.run(['qmicli','-d','qrtr://0','--'+option],capture_output=True,text=True,timeout=30)
 (out/(option+'-private.txt')).write_text(p.stdout+p.stderr)
 lines=[l.strip() for l in (p.stdout+p.stderr).splitlines() if any(x in l for x in ['Operating mode:','Operation mode:','Engine lock:','NMEA types:'])]
 queries[option]=dict(exit=p.returncode,selected_lines=lines)
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')};assert rp==dict(adsp='running',slpi='running',modem='running')
devices=['/sys/bus/i2c/devices/7-0010','/sys/bus/platform/devices/acb3000.camss','/sys/bus/platform/devices/ac4b000.cci']
assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in devices)
packages=subprocess.check_output(['apk','info','-v','libcamera','libcamera-ipa','samurai-camera-config']).decode().splitlines()
assert any('libcamera-99990.7.2-r7'==l for l in packages) and any('samurai-camera-config-0.1.0-r2'==l for l in packages)
import gi
gi.require_version('Qmi','1.0');from gi.repository import Qmi,GObject
methods=[x for x in dir(Qmi.ClientLoc) if any(s in x for s in ['lock','operation_mode','gnss','constellation','system_info'])]
signals=list(GObject.signal_list_names(Qmi.ClientLoc))
(out/'gi-private.json').write_text(json.dumps(dict(methods=methods,signals=signals),indent=2)+'\n')
r=dict(stage=221,current219_boot_authenticated=True,current_camera_stack_preserved=True,modem=properties,gps=gps,queries=queries,remoteprocs=rp,taint=0,loc_methods=methods,read_only_modem_queries=True,no_engine_start_or_reboot=True)
(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=150)
(host.PRIVATE/'baseline-host-private.log').write_bytes(p.stdout+p.stderr)
r=json.loads(p.stdout);(here/'baseline-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
state=json.loads((host.PRIVATE/'current-work-private.json').read_text());state.update(guard='/var/lib/samurai/k221-baseline/boot-id-private.txt',state='Read-only GNSS and modem baseline authenticated; no device transition')
(host.PRIVATE/'current-work-private.json').write_text(json.dumps(state,indent=2)+'\n')
