"""Watch desktop-driven rotation without claiming sensors or setting transforms."""
from pathlib import Path
import importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel269')
spec=importlib.util.spec_from_file_location('h',R/'host.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
code=r'''
from pathlib import Path
import gi,json,os,pwd,subprocess,time
gi.require_version('Gio','2.0')
from gi.repository import Gio,GLib
out=Path('/var/lib/samurai/k269-rotation-watch-r1');out.mkdir(mode=0o700)
system=Gio.bus_get_sync(Gio.BusType.SYSTEM,None)
p=next(p for p in Path('/proc').glob('[0-9]*') if (p/'comm').exists() and (p/'comm').read_text().strip()=='phosh')
raw={k.decode():v.decode() for x in (p/'environ').read_bytes().split(b'\0') if b'=' in x for k,v in [x.split(b'=',1)]}
env={k:v for k,v in raw.items() if k in ['PATH','HOME','USER','LOGNAME','LANG','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','WAYLAND_DISPLAY']}
u=pwd.getpwuid(10000)
def demote():os.initgroups(u.pw_name,u.pw_gid);os.setgid(u.pw_gid);os.setuid(u.pw_uid)
records=[];start=time.monotonic()
for n in range(120):
 props=system.call_sync('net.hadess.SensorProxy','/net/hadess/SensorProxy','org.freedesktop.DBus.Properties','GetAll',GLib.Variant('(s)',('net.hadess.SensorProxy',)),None,Gio.DBusCallFlags.NONE,3000,None).unpack()[0]
 q=subprocess.run(['gdbus','call','--session','--dest','org.gnome.Mutter.DisplayConfig','--object-path','/org/gnome/Mutter/DisplayConfig','--method','org.gnome.Mutter.DisplayConfig.GetCurrentState'],env=env,preexec_fn=demote,capture_output=True,text=True,timeout=4)
 assert q.returncode==0;state=GLib.Variant.parse(None,q.stdout,None,None).unpack()
 records.append(dict(seconds=round(time.monotonic()-start,2),orientation=props['AccelerometerOrientation'],transform=state[2][0][3]))
 (out/'observations.json').write_text(json.dumps(records,indent=2)+'\n');time.sleep(.5)
changes=[]
for row in records:
 if not changes or (row['orientation'],row['transform'])!=(changes[-1]['orientation'],changes[-1]['transform']):changes.append(row)
report=dict(stage=269,records=len(records),changes=changes,seconds=round(time.monotonic()-start,2),
 observer_did_not_claim_accelerometer=True,observer_did_not_set_display_transform=True,
 physical_sequence_confirmation_pending=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
q=h.ssh('python3 -',input=code.encode(),timeout=100);(P/'rotation-watch-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
(R/'rotation-watch-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
