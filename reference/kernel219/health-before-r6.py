from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import dbus,hashlib,json,os,subprocess
root=Path('/var/lib/samurai');out=root/'k219-before-r6-health';assert not out.exists();out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k219-runtime/boot-id-private.txt').read_bytes()
tree=Path('/usr/lib/modules')/os.uname().release;count=0
for line in (root/'k219-before-reboot/module-tree.sha256').read_text().splitlines():
 digest,name=line.split(maxsplit=1);name=name.lstrip(' *');path=tree/name
 if path.name=='imx471.ko':digest='e49dab26b05a325df8da64bb5c4b57c29cd51d1dcf15f5d4ed4dcb53033e66f1'
 assert hashlib.sha256(path.read_bytes()).hexdigest()==digest;count+=1
assert count==786 and len(list(tree.rglob('*.ko')))==772
assert Path('/lib/apk/db/installed').read_bytes()==(root/'k219-baseline/installed-before-private.txt').read_bytes()
old=json.loads((root/'k214-package-candidates/forward-manifest.json').read_text());files=0
for package in old['packages']:
 for name,item in package['files'].items():
  p=Path('/')/name
  if item['kind']=='symlink':assert p.is_symlink() and os.readlink(p)==item['target']
  else:assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256']
  files+=1
assert Path('/sys/module/imx471/parameters/unprocessed_fullres').read_text().strip()=='N'
devices=['/sys/bus/i2c/devices/7-0010','/sys/bus/platform/devices/acb3000.camss','/sys/bus/platform/devices/ac4b000.cci'];assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in devices)
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')};assert rp==dict(adsp='running',slpi='running',modem='running')
log=subprocess.check_output(['dmesg']);(out/'dmesg-private.txt').write_bytes(log)
faults={k:log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()};assert not any(faults.values()) and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
bus=dbus.SystemBus(private=True)
objects=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();modems=[p for p,v in objects.items() if 'org.freedesktop.ModemManager1.Modem' in v];assert len(modems)==1
props=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1',modems[0]),'org.freedesktop.DBus.Properties');loc=props.GetAll('org.freedesktop.ModemManager1.Modem.Location')
assert int(loc['Enabled'])==0 and not loc['SignalsLocation'] and int(loc['GpsRefreshRate'])==30
objects=dbus.Interface(bus.get_object('org.bluez','/'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();adapters=[v['org.bluez.Adapter1'] for v in objects.values() if 'org.bluez.Adapter1' in v]
assert len(adapters)==1 and not adapters[0]['Powered'] and not adapters[0]['Discovering'] and not any(v.get('org.bluez.Device1',{}).get('Connected',False) for v in objects.values());bus.close()
processes={n:0 for n in ['wireplumber','pipewire','phosh','phoc']}
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  name=(p/'comm').read_text().strip()
  if name in processes and int((p/'status').read_text().split('Uid:',1)[1].split()[0])==10000:processes[name]+=1
 except OSError:pass
assert all(v==1 for v in processes.values())
r=dict(stage=219,same_current_boot=True,module_tree_files_verified=count,modules_count=772,
 only_sensor_module_changed_from_initial219_boot=True,all_r5_camera_payloads_verified=files,installed_944_package_database_preserved=True,
 experimental_full_mode_disabled=True,camera_devices_suspended=True,remoteprocs=rp,user_process_counts=processes,
 gps_enabled=0,signals_location=False,gps_refresh_rate=30,bt_powered=False,bt_discovering=False,bt_connections=0,
 taint=0,fault_counts=faults,uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),no_device_mutation=True)
(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=100);(host.PRIVATE/'before-r6-health-host-private.log').write_bytes(p.stdout+p.stderr)
r=json.loads(p.stdout);(here/'before-r6-health-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
