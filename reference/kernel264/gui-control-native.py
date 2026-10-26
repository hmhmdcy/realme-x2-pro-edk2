"""Inspect and operate only the owned Snapshot window through its public accessibility API."""
from pathlib import Path
import hashlib,json,os,pwd,sys,time
import gi
gi.require_version('Gio','2.0')
from gi.repository import Gio,GLib
mode=sys.argv[1];assert mode in ['scan','capture']
root=Path('/var/lib/samurai/k264-snapshot-gui');state=json.loads((root/'state-private.json').read_text());pid=state['capture_pid']
assert Path('/proc',str(pid),'comm').read_text().strip()=='snapshot'
request=None
if mode=='capture':
 request=json.loads(sys.argv[2]);assert request['pid']==pid
 (root/'shutter-request-private.json').write_text(json.dumps(dict(app_pid=pid,at_monotonic=time.monotonic(),accessible=request),indent=2)+'\n')
summary_file=(root/'gui-control-summary-private.json').open('w') if mode=='capture' else None
pictures=json.loads((root/'pictures-before-private.json').read_text())
desktop=next(p for p in Path('/proc').glob('[0-9]*') if (p/'comm').exists() and (p/'comm').read_text().strip()=='phosh');raw={k.decode():v.decode() for x in (desktop/'environ').read_bytes().split(b'\0') if b'=' in x for k,v in [x.split(b'=',1)]}
env={k:v for k,v in raw.items() if k in ['PATH','HOME','USER','LOGNAME','LANG','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','WAYLAND_DISPLAY','DISPLAY']}
user=pwd.getpwuid(10000);os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid);os.environ.clear();os.environ.update(env)
session=Gio.bus_get_sync(Gio.BusType.SESSION,None)
def call(conn,dest,path,interface,method,parameters=None,timeout=1500):return conn.call_sync(dest,path,interface,method,parameters,None,Gio.DBusCallFlags.NONE,timeout,None).unpack()
address=call(session,'org.a11y.Bus','/org/a11y/bus','org.a11y.Bus','GetAddress')[0]
bus=Gio.DBusConnection.new_for_address_sync(address,Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT|Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION,None,None)
def owner_pid(name):return call(bus,'org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','GetConnectionUnixProcessID',GLib.Variant('(s)',(name,)))[0]
def props(name,path):return call(bus,name,path,'org.freedesktop.DBus.Properties','GetAll',GLib.Variant('(s)',('org.a11y.atspi.Accessible',)))[0]
if mode=='scan':
 children=call(bus,'org.a11y.atspi.Registry','/org/a11y/atspi/accessible/root','org.a11y.atspi.Accessible','GetChildren')[0]
 starts=[(name,path) for name,path in children if owner_pid(name)==pid];assert starts,'Owned Snapshot is not present in accessibility tree'
 queue=[(name,path,0) for name,path in starts];seen=set();entries=[]
 while queue and len(entries)<200:
  name,path,depth=queue.pop(0)
  if (name,path) in seen:continue
  seen.add((name,path));p=props(name,path)
  try:role=call(bus,name,path,'org.a11y.atspi.Accessible','GetRoleName')[0]
  except GLib.Error:role=None
  try:actions=call(bus,name,path,'org.a11y.atspi.Action','GetActions')[0]
  except GLib.Error:actions=[]
  entries.append(dict(pid=pid,bus=name,path=path,name=p.get('Name'),description=p.get('Description'),role=role,actions=actions,depth=depth))
  if depth<12:
   try:more=call(bus,name,path,'org.a11y.atspi.Accessible','GetChildren')[0]
   except GLib.Error:more=[]
   queue.extend((n or name,p,depth+1) for n,p in more)
 print(json.dumps(dict(pid=pid,entries=entries)),flush=True)
else:
 assert owner_pid(request['bus'])==pid
 p=props(request['bus'],request['path']);assert p['Name']==request['name']
 actions=call(bus,request['bus'],request['path'],'org.a11y.atspi.Action','GetActions')[0]
 assert request['action_name']=='win.take-picture' and actions[request['action_index']][0]==request['action_name']
 accepted=call(bus,request['bus'],request['path'],'org.a11y.atspi.Action','DoAction',GLib.Variant('(i)',(request['action_index'],)))[0];assert accepted
 before=set(pictures['files']);directory=Path(pictures['root']);deadline=time.monotonic()+15;new=[]
 while time.monotonic()<deadline:
  new=[p for p in directory.rglob('*') if p.is_file() and p.suffix.lower() in ['.jpg','.jpeg'] and str(p) not in before and p.stat().st_size>1024]
  if new:break
  time.sleep(.2)
 assert new,'Shutter action did not save a new JPEG'
 time.sleep(.4);photos=[dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in new]
 call(session,'org.gnome.Snapshot','/org/gnome/Snapshot','org.gtk.Actions','Activate',GLib.Variant('(sava{sv})',('quit',[],{})))
 report=dict(app_pid=pid,accessible_shutter_action_accepted=True,new_jpegs=photos,quit_action_sent=True)
 summary_file.write(json.dumps(report,indent=2)+'\n');summary_file.flush();summary_file.close();print(json.dumps(report),flush=True)
