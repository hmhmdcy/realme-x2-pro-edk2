"""Read actual current payloads, module identities, idle supplies/clocks and normal services."""
from pathlib import Path
import ast,json
import host
R=Path(__file__).resolve().parent
t=ast.parse((R.parent/'kernel276/test-manager-lifetime.py').read_text());n=next(n for n in t.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='code' for x in n.targets) and isinstance(n.value,ast.Call));source=ast.literal_eval(n.value.func.value);source=source[:source.index('save();report={}')].replace('k276-manager-lifetime-r1','k277-final-health')
source+=r'''
import dbus,struct
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k276-work/boot-id-private.txt').read_bytes()
h=health();assert h['passed']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def note(p):
 b=Path(p).read_bytes();offset=struct.unpack_from('<Q',b,40)[0];size,count,index=struct.unpack_from('<HHH',b,58);sec=[struct.unpack_from('<IIQQQQIIQQ',b,offset+i*size) for i in range(count)];names=b[sec[index][4]:sec[index][4]+sec[index][5]]
 return next(b[s[4]:s[4]+s[5]] for s in sec if names[s[0]:].split(b'\0',1)[0]==b'.note.gnu.build-id')
manifest=json.loads(Path('/var/lib/samurai/k277-package-transaction/new-manifest-private.json').read_text());checked=0
for pkg in manifest['packages']:
 for name,item in pkg['files'].items():
  p=Path('/')/name
  if item['kind']=='symlink':assert p.is_symlink() and os.readlink(p)==item['target']
  else:assert not p.is_symlink() and sha(p)==item['sha256'] and (p.stat().st_mode&0o777)==item['mode']
  checked+=1
tree=Path('/usr/lib/modules')/os.uname().release;old=json.loads(Path('/var/lib/samurai/k277-package-transaction/module-inventory-before-private.json').read_text());now={str(p.relative_to(tree)):sha(p) for p in tree.rglob('*.ko')};changed=[n for n in now if now[n]!=old[n]]
assert len(now)==776 and set(now)==set(old) and changed==[]
modules={}
for name in ['qcom_pm8008','qcom_pm8008_regulator','imx319','imx471','qcom_camss','v4l2_cci','s5k3m5','s5kgw1','lc898219xi','i2c_qcom_cci']:
 p=Path(subprocess.check_output(['modinfo','-n',name],text=True).strip());match=Path('/sys/module',name,'notes/.note.gnu.build-id').read_bytes()==note(p);assert match
 modules[name]=dict(sha256=sha(p),loaded=True,loaded_note_matches_disk=match)
services=json.loads(Path('/var/lib/samurai/k277-services-verified-private.json').read_text())['processes'];maps={}
for row in services:
 p=Path('/proc',str(row['pid']));fields=(p/'stat').read_text().rsplit(')',1)[1].split();assert fields[0]!='Z' and fields[19]==row['start_ticks'] and (p/'comm').read_text().strip()==row['comm']
 if row['comm'] in ['pipewire','wireplumber']:
  text=(p/'maps').read_text();assert not any('/var/lib/samurai/k' in l and '.so' in l for l in text.splitlines()) and not any('libcamera' in l and '(deleted)' in l for l in text.splitlines())
  maps[row['comm']]=dict(normal_library_paths=True,spa_mapped='/usr/lib/spa-0.2/libcamera/libspa-libcamera.so' in text)
assert maps['wireplumber']['spa_mapped']
db=Path('/lib/apk/db/installed').read_bytes();package_count=sum(1 for b in db.split(b'\n\n') if any(l.startswith(b'P:') for l in b.splitlines()));assert package_count==961
kernel=subprocess.check_output(['dmesg'],text=True);cci_errors=[l for l in kernel.splitlines() if 'i2c-qcom-cci' in l and any(s in l.lower() for s in ['timeout','failed','nack'])];assert not cci_errors
ssc=json.loads(Path('/run/samurai-ssc/state.json').read_text());bus=dbus.SystemBus(private=True)
try:
 props=dbus.Interface(bus.get_object('net.hadess.SensorProxy','/net/hadess/SensorProxy'),'org.freedesktop.DBus.Properties').GetAll('net.hadess.SensorProxy');sensor_proxy={k:bool(props.get(k,False)) for k in ['HasAccelerometer','HasAmbientLight','HasProximity']}
finally:bus.close()
cci_node=Path('/sys/bus/platform/devices/ac4a000.cci/of_node');supply=(cci_node/'vddio-supply').read_bytes();target=next(p.parent for p in Path('/sys/firmware/devicetree/base').rglob('phandle') if p.read_bytes()==supply);io=next(p for p in Path('/sys/class/regulator').glob('regulator.*') if (p/'of_node').exists() and (p/'of_node').resolve()==target)
io_state={k:(io/k).read_text().strip() for k in ['state','num_users','microvolts']};assert io_state['state']=='disabled' and io_state['num_users']=='0'
pstore=[p.name for p in Path('/sys/fs/pstore').glob('*') if p.is_file()];assert not pstore
report=dict(stage=277,release=os.uname().release,kernel_build=183,module_count=776,package_count=package_count,current49_payloads_verified=checked,all776_modules_unchanged=True,modules=modules,
 camera_idle_health=h,shared_io_supply=io_state,services=services,desktop_library_maps=maps,package_versions={p['name']:p['version'] for p in manifest['packages']},
 ssc_started=bool(ssc.get('started')),sensor_proxy=sensor_proxy,normal_desktop_start_observed=True,rotation_physical_retest_not_performed=True,cci_errors=cci_errors,pstore=pstore,
 no_spectra_hardware_image_processing=True,autofocus_algorithm_not_implemented=True)
(root/'summary-private.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
q=host.ssh('python3 -',input=source.encode(),timeout=35);(host.PRIVATE/'final-health-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
(R/'final-health-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps({k:v for k,v in d.items() if k not in ['modules','camera_idle_health']},indent=2))
