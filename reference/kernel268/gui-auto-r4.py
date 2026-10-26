"""Operate only the owned Snapshot through observed AT-SPI actions."""
from pathlib import Path
import hashlib,json,os,pwd,re,time,traceback
import gi
gi.require_version('Gio','2.0')
from gi.repository import Gio,GLib
root=Path('/var/lib/samurai/k268-snapshot-gui-r4');state=json.loads((root/'state-private.json').read_text());pid=state['capture_pid']
assert Path('/proc',str(pid),'comm').read_text().strip()=='snapshot'
pictures=json.loads((root/'pictures-before-private.json').read_text());summary_file=(root/'gui-control-summary-private.json').open('w');request_file=(root/'shutter-request-private.json').open('w')
tree_file=(root/'accessible-tree-private.json').open('w')

desktop=next(p for p in Path('/proc').glob('[0-9]*') if (p/'comm').exists() and (p/'comm').read_text().strip()=='phosh')
raw={k.decode():v.decode() for x in (desktop/'environ').read_bytes().split(b'\0') if b'=' in x for k,v in [x.split(b'=',1)]}
env={k:v for k,v in raw.items() if k in ['PATH','HOME','USER','LOGNAME','LANG','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','WAYLAND_DISPLAY','DISPLAY']}
u=pwd.getpwuid(10000);os.initgroups(u.pw_name,u.pw_gid);os.setgid(u.pw_gid);os.setuid(u.pw_uid);os.environ.clear();os.environ.update(env)
session=Gio.bus_get_sync(Gio.BusType.SESSION,None)
def call(conn,dest,path,interface,method,parameters=None,timeout=1500):
 return conn.call_sync(dest,path,interface,method,parameters,None,Gio.DBusCallFlags.NONE,timeout,None).unpack()
address=call(session,'org.a11y.Bus','/org/a11y/bus','org.a11y.Bus','GetAddress')[0]
bus=Gio.DBusConnection.new_for_address_sync(address,Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT|Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION,None,None)
def owner_pid(name):return call(bus,'org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','GetConnectionUnixProcessID',GLib.Variant('(s)',(name,)))[0]
def scan(target_pid=pid):
 children=call(bus,'org.a11y.atspi.Registry','/org/a11y/atspi/accessible/root','org.a11y.atspi.Accessible','GetChildren')[0]
 queue=[(n,p,0) for n,p in children if owner_pid(n)==target_pid];seen=set();entries=[]
 while queue and len(entries)<1200:
  name,path,depth=queue.pop(0)
  if (name,path) in seen:continue
  seen.add((name,path))
  props=call(bus,name,path,'org.freedesktop.DBus.Properties','GetAll',GLib.Variant('(s)',('org.a11y.atspi.Accessible',)))[0]
  try:actions=call(bus,name,path,'org.a11y.atspi.Action','GetActions')[0]
  except GLib.Error:actions=[]
  entries.append(dict(bus=name,path=path,name=props.get('Name'),description=props.get('Description'),depth=depth,actions=actions))
  if depth<64:
   try:more=call(bus,name,path,'org.a11y.atspi.Accessible','GetChildren')[0]
   except GLib.Error:more=[]
   queue.extend((n or name,p,depth+1) for n,p in more)
 return entries
def action(entries,names):
 found=[dict(**e,action_name=a[0],action_index=i) for e in entries for i,a in enumerate(e['actions']) if a[0] in names]
 assert len(found)<=1,('ambiguous observed action',names)
 return found[0] if found else None
def click(a,target_pid=pid):
 assert owner_pid(a['bus'])==target_pid
 actions=call(bus,a['bus'],a['path'],'org.a11y.atspi.Action','GetActions')[0]
 assert actions[a['action_index']][0]==a['action_name']
 assert call(bus,a['bus'],a['path'],'org.a11y.atspi.Action','DoAction',GLib.Variant('(i)',(a['action_index'],)))[0]
def active(which):
 selected='/sys/bus/i2c/devices/'+('9-0010' if which=='front' else '7-0010')+'/power/runtime_status'
 other='/sys/bus/i2c/devices/'+('7-0010' if which=='front' else '9-0010')+'/power/runtime_status'
 return Path(selected).read_text().strip()=='active' and Path(other).read_text().strip()=='suspended'
def await_camera(which,seconds=12):
 deadline=time.monotonic()+seconds
 while time.monotonic()<deadline:
  if active(which):time.sleep(2);return True
  time.sleep(.2)
 return False
def photos():return {str(p) for p in Path(pictures['root']).rglob('*') if p.is_file() and p.suffix.lower() in ['.jpg','.jpeg'] and p.stat().st_size>1024}
events=[];captured=[]
def shutter(which):
 entries=scan();a=action(entries,{'win.take-picture'});assert a,'No observed shutter action'
 before=photos();click(a);events.append(dict(camera=which,action=a,at_monotonic=time.monotonic()))
 request_file.seek(0);request_file.write(json.dumps(events,indent=2));request_file.truncate();request_file.flush()
 deadline=time.monotonic()+12
 while time.monotonic()<deadline:
  new=photos()-before
  if new:break
  time.sleep(.2)
 assert new,'No new JPEG for '+which
 time.sleep(.4)
 for name in sorted(new):
  p=Path(name);captured.append(dict(camera=which,path=name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
try:
 deadline=time.monotonic()+15
 while time.monotonic()<deadline:
  try:
   entries=scan()
   if entries:break
  except GLib.Error:pass
  time.sleep(.3)
 phosh_pid=int(desktop.name)
 shell_entries=scan(phosh_pid)
 launches=[dict(**e,action_name=a[0],action_index=i) for e in shell_entries for i,a in enumerate(e['actions'])
  if e.get('name')=='Camera (Snapshot)' and a[0]=='Click']
 assert len(launches)==1,'Observed Camera (Snapshot) desktop launcher is not unique'
 assert Path('/proc',str(pid),'comm').read_text().strip()=='snapshot'
 click(launches[0],phosh_pid)
 assert await_camera('front'),'Front sensor not active for owned window'
 time.sleep(3);shutter('front')
 entries=scan();tree_file.write(json.dumps(entries,indent=2));tree_file.flush()
 switch=action(entries,{'win.next-camera','win.switch-camera','win.change-camera','win.toggle-camera'})
 if switch is None:
  candidates=[dict(**e,action_name=a[0],action_index=i) for e in entries for i,a in enumerate(e['actions'])
   if re.search(r'(switch|change|flip|toggle).*(camera)|camera.*(switch|change)|切换.*(摄像头|相机)',
                str(e.get('name') or '')+' '+str(e.get('description') or ''),re.I)]
  assert len(candidates)<=1,'Ambiguous labelled camera control'
  switch=candidates[0] if candidates else None
 switched=False
 if switch:
  click(switch);time.sleep(.5)
  if not active('rear'):
   entries=scan();tree_file.seek(0);tree_file.truncate();tree_file.write(json.dumps(entries,indent=2));tree_file.flush()
   candidates=[dict(**e,action_name=a[0],action_index=i) for e in entries for i,a in enumerate(e['actions'])
    if re.search(r'Built.in Back Camera|Back Camera|后置',str(e.get('name') or ''),re.I)]
   assert len(candidates)<=1,'Ambiguous rear-camera menu action'
   if candidates:click(candidates[0])
  switched=await_camera('rear')
  assert switched,'Observed switch action did not activate rear sensor'
  shutter('rear')
 report=dict(app_pid=pid,accessible_shutter_action_accepted=True,observed_desktop_launcher_clicked=True,new_jpegs=captured,camera_switch_action_found=switch is not None,camera_switch_action_accepted=switched,observed_actions=sorted(set(a[0] for e in entries for a in e['actions'])),quit_action_sent=True)
 summary_file.write(json.dumps(report,indent=2)+'\n');summary_file.flush()
 call(session,'org.gnome.Snapshot','/org/gnome/Snapshot','org.gtk.Actions','Activate',GLib.Variant('(sava{sv})',('quit',[],{})))
 print(json.dumps(dict(success=True,photos=len(captured),rear_switch=switched)),flush=True)
except BaseException:
 summary_file.seek(0);summary_file.truncate()
 summary_file.write(json.dumps(dict(error=traceback.format_exc(),new_jpegs=captured),indent=2)+'\n');summary_file.flush();raise
finally:summary_file.close();request_file.close();tree_file.close()

