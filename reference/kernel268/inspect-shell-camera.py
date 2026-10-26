"""Read observed camera launch actions in the current Phosh overview."""
import json
import host

code=r'''
from pathlib import Path
import gi,json,os,pwd
gi.require_version('Gio','2.0')
from gi.repository import Gio,GLib
r=Path('/var/lib/samurai');desktop=next(p for p in Path('/proc').glob('[0-9]*') if (p/'comm').exists() and (p/'comm').read_text().strip()=='phosh');pid=int(desktop.name)
env={k.decode():v.decode() for x in (desktop/'environ').read_bytes().split(b'\0') if b'=' in x for k,v in [x.split(b'=',1)]}
u=pwd.getpwuid(10000);os.initgroups(u.pw_name,u.pw_gid);os.setgid(u.pw_gid);os.setuid(u.pw_uid);os.environ.update({k:env[k] for k in ['DBUS_SESSION_BUS_ADDRESS','XDG_RUNTIME_DIR']})
def call(conn,dest,path,iface,method,args=None):return conn.call_sync(dest,path,iface,method,args,None,Gio.DBusCallFlags.NONE,1500,None).unpack()
session=Gio.bus_get_sync(Gio.BusType.SESSION,None)
address=call(session,'org.a11y.Bus','/org/a11y/bus','org.a11y.Bus','GetAddress')[0]
bus=Gio.DBusConnection.new_for_address_sync(address,Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT|Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION,None,None)
children=call(bus,'org.a11y.atspi.Registry','/org/a11y/atspi/accessible/root','org.a11y.atspi.Accessible','GetChildren')[0]
queue=[]
for n,p in children:
 owner=call(bus,'org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','GetConnectionUnixProcessID',GLib.Variant('(s)',(n,)))[0]
 if owner==pid:queue.append((n,p,0))
seen=set();entries=[]
while queue and len(entries)<1200:
 n,p,depth=queue.pop(0)
 if (n,p) in seen:continue
 seen.add((n,p));props=call(bus,n,p,'org.freedesktop.DBus.Properties','GetAll',GLib.Variant('(s)',('org.a11y.atspi.Accessible',)))[0]
 try:actions=call(bus,n,p,'org.a11y.atspi.Action','GetActions')[0]
 except GLib.Error:actions=[]
 try:states=call(bus,n,p,'org.a11y.atspi.Accessible','GetState')[0]
 except GLib.Error:states=[]
 entries.append(dict(bus=n,path=p,name=props.get('Name'),description=props.get('Description'),actions=actions,states=states))
 if depth<20:
  try:more=call(bus,n,p,'org.a11y.atspi.Accessible','GetChildren')[0]
  except GLib.Error:more=[]
  queue.extend((a or n,b,depth+1) for a,b in more)
try:
 gi.require_version('Atspi','2.0')
 from gi.repository import Atspi
 state_names=dict(showing=int(Atspi.StateType.SHOWING),visible=int(Atspi.StateType.VISIBLE),sensitive=int(Atspi.StateType.SENSITIVE))
except (ValueError,ImportError):state_names={}
print(json.dumps(dict(owner_pid=pid,entries=entries,state_names=state_names)))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=30)
(host.PRIVATE/'shell-accessible-private.json').write_bytes(q.stdout)
d=json.loads(q.stdout)
print(json.dumps(dict(phosh_pid=d['owner_pid'],entries=len(d['entries']),state_names=d['state_names'],
 visible_actions=[dict(name=e.get('name'),description=e.get('description'),actions=e['actions'],path=e['path']) for e in d['entries'] if e['actions'] and e.get('states') and e['states'][0]&(1<<25)],
 camera_controls=[e for e in d['entries'] if any(x in str(e.get('name') or '').lower() for x in ['camera','snapshot','相机'])])))
