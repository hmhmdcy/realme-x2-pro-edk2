from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import dbus,hashlib,json,os,re,shutil,stat,subprocess
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k214-baseline';assert not out.exists()
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(root/'k213-baseline/boot-id-private.txt').read_bytes()
assert Path('/sys/firmware/devicetree/base/model').read_bytes()==b'Realme X2 Pro (RMX1931CN)\0' and os.uname().version.startswith('#183 ')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
original=json.loads((root/'k213-baseline/products-before-private.json').read_text());assert all(sha(name)==digest for name,digest in original.items())
db=Path('/lib/apk/db/installed').read_bytes();assert db==(root/'k213-baseline/apk-installed-before-private.txt').read_bytes()
log=subprocess.check_output(['dmesg']);faults={k:log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()};assert not any(faults.values()) and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')};assert len(rp)==3 and all(v=='running' for v in rp.values())
devices={'sensor':'/sys/bus/i2c/devices/7-0010','camss':'/sys/bus/platform/devices/acb3000.camss','cci':'/sys/bus/platform/devices/ac4b000.cci'};pm={k:Path(v,'power/runtime_status').read_text().strip() for k,v in devices.items()};assert all(v=='suspended' for v in pm.values())
rails={}
for p in Path('/sys/class/regulator').glob('regulator.*'):
    if (p/'name').read_text().strip() in ['cam-front-vdig','cam-front-vana']:rails[(p/'name').read_text().strip()]={n:(p/n).read_text().strip() for n in ['state','num_users','microvolts']}
assert len(rails)==2 and all(v['state']=='disabled' and v['num_users']=='0' for v in rails.values())
for name in ['imx471 7-0010','msm_csid0']:
    nodes=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()==name];assert len(nodes)==1
    pattern=subprocess.check_output(['v4l2-ctl','-d','/dev/'+nodes[0].name,'--get-ctrl=test_pattern'],text=True);assert re.search(r'^test_pattern:\s*0(?:\s|\(|$)',pattern)
bus=dbus.SystemBus(private=True);location=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties').GetAll('org.freedesktop.ModemManager1.Modem.Location');assert int(location['Enabled'])==0 and not location['SignalsLocation'] and int(location['GpsRefreshRate'])==30
objects=dbus.Interface(bus.get_object('org.bluez','/'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();adapters=[v['org.bluez.Adapter1'] for v in objects.values() if 'org.bluez.Adapter1' in v];assert len(adapters)==1 and not adapters[0]['Powered'] and not any(v.get('org.bluez.Device1',{}).get('Connected',False) for v in objects.values());bus.close()
out.mkdir(mode=0o700);(out/'boot-id-private.txt').write_bytes(boot);(out/'apk-installed-before-private.txt').write_bytes(db);(out/'dmesg-private.txt').write_bytes(log)
versions={}
for entry in db.decode().split('\n\n'):
    fields={line[0]:line[2:] for line in entry.splitlines() if len(line)>1 and line[1]==':' and line[0] in ['P','V']}
    if fields.get('P') in ['libcamera','libcamera-ipa','libcamera-tools']:versions[fields['P']]=fields['V']
assert versions=={name:'99990.7.2-r4' for name in ['libcamera','libcamera-ipa','libcamera-tools']}
paths={Path('/etc/apk/world'),Path('/etc/libcamera/configuration.yaml'),Path('/etc/modules-load.d/samurai-camera-heaps.conf'),Path('/etc/udev/rules.d/70-samurai-camera-heaps.rules')}
for name in versions:
    lines=subprocess.check_output(['apk','info','-L',name],text=True).splitlines()[1:]
    for relative in lines:
        relative=relative.strip()
        if not relative:continue
        assert not relative.startswith('/') and '..' not in Path(relative).parts;paths.add(Path('/')/relative)
records={}
for path in sorted(paths):
    name=str(path).removeprefix('/')
    if path.is_symlink():records[name]=dict(kind='symlink',target=str(path.readlink()))
    elif path.is_file():
        target=out/'files'/name;target.parent.mkdir(parents=True,exist_ok=True,mode=0o700);shutil.copyfile(path,target);records[name]=dict(kind='file',sha256=sha(path),mode=stat.S_IMODE(path.stat().st_mode))
    elif not path.is_dir():records[name]=dict(kind='absent')
(out/'original-files-manifest-private.json').write_text(json.dumps(records,indent=2)+'\n');(out/'products-before-private.json').write_text(json.dumps(original,indent=2)+'\n')
report=dict(stage=214,fresh_same213_boot_verified=True,installed_camera_products_and_package_database_unchanged=True,original_camera_versions=versions,original_camera_file_records_backed_up=len(records),remoteprocs=rp,camera_devices_pm=pm,front_rails_disabled_zero_users=True,all_test_patterns_disabled=True,taint=0,fault_counts=faults,gps_enabled=0,signals_location=False,gps_refresh_rate=30,bt_powered=False,bt_connections=0,no_flash_reboot_or_product_install_sent=True,uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]))
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=80);(host.PRIVATE/'baseline-host-private.log').write_bytes(p.stdout+p.stderr);report=json.loads(p.stdout);(here/'baseline-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
