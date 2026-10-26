"""Observe one user-confirmed pose through standard SensorProxy and display D-Bus."""
from pathlib import Path
import importlib.util,json,sys
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel269')
spec=importlib.util.spec_from_file_location('h',R/'host.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
pose=sys.argv[1];assert pose in ['normal','left-up','right-up','normal-return']
code=r'''
from pathlib import Path
import gi,json,os,pwd,subprocess,time
gi.require_version('Gio','2.0')
from gi.repository import Gio,GLib
system=Gio.bus_get_sync(Gio.BusType.SYSTEM,None)
def sensor(method,params=None,interface='net.hadess.SensorProxy'):
 return system.call_sync('net.hadess.SensorProxy','/net/hadess/SensorProxy',interface,method,params,None,Gio.DBusCallFlags.NONE,5000,None).unpack()
def properties():return sensor('GetAll',GLib.Variant('(s)',('net.hadess.SensorProxy',)),'org.freedesktop.DBus.Properties')[0]
before=properties();observations=[]
try:
 sensor('ClaimAccelerometer')
 for n in range(10):
  time.sleep(.5);observations.append(properties()['AccelerometerOrientation'])
finally:sensor('ReleaseAccelerometer')
p=next(p for p in Path('/proc').glob('[0-9]*') if (p/'comm').exists() and (p/'comm').read_text().strip()=='phosh')
raw={k.decode():v.decode() for x in (p/'environ').read_bytes().split(b'\0') if b'=' in x for k,v in [x.split(b'=',1)]}
env={k:v for k,v in raw.items() if k in ['PATH','HOME','USER','LOGNAME','LANG','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','WAYLAND_DISPLAY']}
u=pwd.getpwuid(10000)
def demote():os.initgroups(u.pw_name,u.pw_gid);os.setgid(u.pw_gid);os.setuid(u.pw_uid)
def dbus(dest,path,method):
 return subprocess.run(['gdbus','call','--session','--dest',dest,'--object-path',path,'--method',method],env=env,preexec_fn=demote,capture_output=True,text=True,timeout=5)
q=dbus('org.gnome.Mutter.DisplayConfig','/org/gnome/Mutter/DisplayConfig','org.gnome.Mutter.DisplayConfig.GetCurrentState');assert q.returncode==0
state=GLib.Variant.parse(None,q.stdout,None,None).unpack()
screen=dbus('org.gnome.ScreenSaver','/org/gnome/ScreenSaver','org.gnome.ScreenSaver.GetActive')
report=dict(stage=269,physical_pose=POSE,user_confirmed_physical_pose=True,before_orientation=before['AccelerometerOrientation'],
 sensor_orientations=observations,logical_displays=[dict(x=m[0],y=m[1],scale=m[2],transform=m[3],primary=m[4]) for m in state[2]],
 screensaver_response=screen.stdout.strip(),matrix='-1,0,0;0,-1,0;0,0,1',
 standard_sensor_proxy_claim_released=True,no_manual_display_rotation=True)
print(json.dumps(report))
'''.replace('POSE',repr(pose))
q=h.ssh('python3 -',input=code.encode(),timeout=25);d=json.loads(q.stdout)
(P/('rotation-pose-'+pose+'-private.json')).write_bytes(q.stdout)
(R/('rotation-pose-'+pose+'-validation.json')).write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
