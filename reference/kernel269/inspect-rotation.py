"""Read the current sensor-to-display rotation path without changing orientation."""
from pathlib import Path
import importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel269')
spec=importlib.util.spec_from_file_location('current',R/'host.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
code=r'''
from pathlib import Path
import hashlib,json,os,pwd,subprocess,gi
gi.require_version('Gio','2.0')
from gi.repository import Gio,GLib
result={};system=Gio.bus_get_sync(Gio.BusType.SYSTEM,None)
try:
 values=system.call_sync('net.hadess.SensorProxy','/net/hadess/SensorProxy','org.freedesktop.DBus.Properties','GetAll',GLib.Variant('(s)',('net.hadess.SensorProxy',)),None,Gio.DBusCallFlags.NONE,5000,None).unpack()[0]
 result['sensor_proxy']={k:values[k] for k in ['HasAccelerometer','AccelerometerOrientation'] if k in values}
except GLib.Error as e:result['sensor_proxy_error']=str(e)
result['iio']=[]
for p in Path('/sys/bus/iio/devices').glob('iio:device*'):
 values={n:(p/n).read_text().strip() for n in ['name','in_accel_mount_matrix','mount_matrix','in_accel_x_raw','in_accel_y_raw','in_accel_z_raw'] if (p/n).is_file()}
 if any('accel' in k for k in values) or 'mount_matrix' in values:result['iio'].append(values)
result['display_sysfs']={str(p):p.read_text().strip() for p in Path('/sys/class/drm').glob('card*-DSI-*/panel_orientation')}
result['phoc_config']={str(p):p.read_text() for p in [Path('/etc/phoc/phoc.ini'),Path('/etc/phosh/phoc.ini')] if p.is_file()}
result['service_environment']={}
for p in Path('/proc').glob('[0-9]*'):
 try:
  if (p/'comm').read_text().strip().startswith('iio-sensor-prox'):
   result['service_environment']={k.decode():v.decode() for x in (p/'environ').read_bytes().split(b'\0') if b'=' in x for k,v in [x.split(b'=',1)] if k.startswith((b'LIBSSC_',b'IIO_',b'ACCEL_'))}
 except OSError:pass
p=next(p for p in Path('/proc').glob('[0-9]*') if (p/'comm').exists() and (p/'comm').read_text().strip()=='phosh')
raw={k.decode():v.decode() for x in (p/'environ').read_bytes().split(b'\0') if b'=' in x for k,v in [x.split(b'=',1)]}
env={k:v for k,v in raw.items() if k in ['PATH','HOME','USER','LOGNAME','LANG','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','WAYLAND_DISPLAY']}
u=pwd.getpwuid(10000)
def demote():os.initgroups(u.pw_name,u.pw_gid);os.setgid(u.pw_gid);os.setuid(u.pw_uid)
result['settings']={}
for schema in ['org.gnome.settings-daemon.peripherals.touchscreen','sm.puri.phosh']:
 q=subprocess.run(['gsettings','list-recursively',schema],env=env,preexec_fn=demote,capture_output=True,text=True,timeout=5)
 result['settings'][schema]=dict(exit=q.returncode,values='\n'.join(l for l in q.stdout.splitlines() if any(s in l for s in ['orientation','rotation','transform'])))
result['display_dbus']={}
for method in ['GetCurrentState','GetResources']:
 q=subprocess.run(['gdbus','call','--session','--dest','org.gnome.Mutter.DisplayConfig','--object-path','/org/gnome/Mutter/DisplayConfig','--method','org.gnome.Mutter.DisplayConfig.'+method],env=env,preexec_fn=demote,capture_output=True,text=True,timeout=5)
 result['display_dbus'][method]=dict(exit=q.returncode,stdout=q.stdout,stderr=q.stderr)
 if method=='GetCurrentState' and q.returncode==0:
  state=GLib.Variant.parse(None,q.stdout,None,None).unpack()
  result['logical_displays']=[dict(x=m[0],y=m[1],scale=m[2],transform=m[3],primary=m[4]) for m in state[2]]
result['packages']={}
for block in Path('/lib/apk/db/installed').read_text().split('\n\n'):
 row={l[:1]:l[2:] for l in block.splitlines() if len(l)>2 and l[1]==':'}
 if row.get('P') in ['iio-sensor-proxy','phosh','phoc','samurai-libssc']:result['packages'][row['P']]=row.get('V')
print(json.dumps(result))
'''
q=h.ssh('python3 -',input=code.encode(),timeout=35);(P/'rotation-observation-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
print(json.dumps({k:v for k,v in d.items() if k!='display_dbus'},indent=2))
for k,v in d['display_dbus'].items():
 print(k+': '+str(v['exit']))
 # Keep detailed monitor identifiers in the private receipt.
 print(v['stderr'][:500] if v['exit'] else 'Display state retained privately.')
