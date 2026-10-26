"""Install board sensor metadata; retain a reversible, boot-guarded receipt."""
from pathlib import Path
import importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel269')
spec=importlib.util.spec_from_file_location('h',R/'host.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
rule=(R/'99-realme-rmx1931-sensors.rules').read_text()
code=r'''
from pathlib import Path
import hashlib,json,os,subprocess,time,gi
gi.require_version('Gio','2.0')
from gi.repository import Gio,GLib
os.umask(0o077)
assert 'realme,samurai' in Path('/sys/firmware/devicetree/base/compatible').read_bytes().decode().split('\0')
out=Path('/var/lib/samurai/k269-rotation-metadata-r1');out.mkdir(mode=0o700)
dest=Path('/etc/udev/rules.d/99-realme-rmx1931-sensors.rules');assert not dest.exists()
rule=RULE_TEXT
devices=['/sys/devices/virtual/misc/fastrpc-adsp','/sys/devices/virtual/misc/fastrpc-sdsp']
assert all(Path(x).is_dir() for x in devices)
system=Gio.bus_get_sync(Gio.BusType.SYSTEM,None)
def call(dest,path,interface,method,params):
 return system.call_sync(dest,path,interface,method,params,None,Gio.DBusCallFlags.NONE,5000,None).unpack()
def properties():
 return call('net.hadess.SensorProxy','/net/hadess/SensorProxy','org.freedesktop.DBus.Properties','GetAll',GLib.Variant('(s)',('net.hadess.SensorProxy',)))[0]
def owner():
 return call('org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','GetNameOwner',GLib.Variant('(s)',('net.hadess.SensorProxy',)))[0]
def udev(path):
 q=subprocess.run(['udevadm','info','--query=property','--path='+path],capture_output=True,text=True,check=True,timeout=10)
 return dict(l.split('=',1) for l in q.stdout.splitlines() if '=' in l)
def refresh():
 subprocess.run(['udevadm','control','--reload-rules'],check=True,capture_output=True,timeout=10)
 for path in devices:subprocess.run(['udevadm','trigger','--action=change',path],check=True,capture_output=True,timeout=10)
 subprocess.run(['udevadm','settle','--timeout=10'],check=True,capture_output=True,timeout=12)
def restart():
 q=subprocess.run(['rc-service','iio-sensor-proxy','restart'],capture_output=True,timeout=25)
 (out/'service-restart-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
stable=[Path('/etc/conf.d/iio-sensor-proxy'),Path('/etc/phoc/phoc.ini'),Path('/etc/phosh/phoc.ini'),Path('/usr/lib/samurai/ssc/libssc.so.2')]
hashes=lambda:{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in stable}
before=dict(sensor_proxy=properties(),owner=owner(),stable_hashes=hashes(),udev={p:udev(p) for p in devices})
(out/'before-private.json').write_text(json.dumps(before,indent=2))
dmesg=subprocess.check_output(['dmesg'])
try:
 dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(rule);dest.chmod(0o644)
 refresh()
 for p in devices:assert udev(p).get('ACCEL_MOUNT_MATRIX')=='-1,0,0;0,-1,0;0,0,1'
 restart()
 observations=[]
 for n in range(12):
  try:
   props=properties();observations.append(props.get('AccelerometerOrientation'))
   if props.get('HasAccelerometer') and props.get('AccelerometerOrientation')=='normal':break
  except GLib.Error:pass
  time.sleep(1)
 after=dict(sensor_proxy=properties(),owner=owner(),stable_hashes=hashes(),udev={p:udev(p) for p in devices})
 assert after['owner']!=before['owner'] and after['sensor_proxy']['HasAccelerometer']
 assert after['stable_hashes']==before['stable_hashes']
 tail=subprocess.check_output(['dmesg'])
 faults={k:tail.count(v)-dmesg.count(v) for k,v in dict(warn=b'WARNING:',oops=b'Oops:',fatal=b'fatal error received').items()}
 assert not any(faults.values())
 (out/'after-private.json').write_text(json.dumps(after,indent=2))
 report=dict(stage=269,matrix='-1,0,0;0,-1,0;0,0,1',rule_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),
  rule_path=str(dest),board_compatible='realme,samurai',standard_ssc_sensor_proxy_metadata=True,
  only_sensor_proxy_restarted=True,udev_accel_devices_updated=len(devices),
  before_orientation=before['sensor_proxy']['AccelerometerOrientation'],after_orientation=after['sensor_proxy']['AccelerometerOrientation'],
  observed_after_restart=observations,unmodified_service_config_display_config_and_libssc=True,fault_delta=faults,
  availability={k:v for k,v in after['sensor_proxy'].items() if k.startswith('Has')},
  app_or_desktop_source_changed=False,other_physical_poses_not_yet_verified=True)
 (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
except BaseException:
 if dest.exists():dest.unlink()
 refresh();restart()
 (out/'rollback-completed').write_text('Rule removed and original SensorProxy restarted.\n')
 raise
'''.replace('RULE_TEXT',repr(rule))
q=h.ssh('python3 -',input=code.encode(),timeout=80);(P/'rotation-metadata-response-private.json').write_bytes(q.stdout)
d=json.loads(q.stdout);(R/'rotation-metadata-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
