#!/usr/bin/python3
"""A distinct, installed GNSS validation application, never an existing app's identity."""
import dbus,json,math,os,signal,sys,time
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib,GLibUnix

assert os.getuid()==10000
DBusGMainLoop(set_as_default=True);bus=dbus.SystemBus(private=True);loop=GLib.MainLoop()
manager=dbus.Interface(bus.get_object('org.freedesktop.GeoClue2','/org/freedesktop/GeoClue2/Manager'),'org.freedesktop.GeoClue2.Manager')
path=manager.GetClient(timeout=25);obj=bus.get_object('org.freedesktop.GeoClue2',path);client=dbus.Interface(obj,'org.freedesktop.GeoClue2.Client');props=dbus.Interface(obj,'org.freedesktop.DBus.Properties')
result=dict(uid=os.getuid(),desktop_id='org.realme.SamuraiGNSSValidation',started=False,location_events=0,valid_location_events=0,stopped=False)
def changed(old,new):
 result['location_events']+=1
 loc=dbus.Interface(bus.get_object('org.freedesktop.GeoClue2',new),'org.freedesktop.DBus.Properties').GetAll('org.freedesktop.GeoClue2.Location')
 valid=all(math.isfinite(float(loc[n])) for n in ['Latitude','Longitude','Accuracy']) and -90<=float(loc['Latitude'])<=90 and -180<=float(loc['Longitude'])<=180 and float(loc['Accuracy'])>0
 result['valid_location_events']+=int(valid)
def stop(*unused):loop.quit();return False
for sig in [signal.SIGTERM,signal.SIGINT]:GLibUnix.signal_add(GLib.PRIORITY_DEFAULT,sig,stop)
try:
 props.Set('org.freedesktop.GeoClue2.Client','DesktopId',dbus.String(result['desktop_id']))
 props.Set('org.freedesktop.GeoClue2.Client','RequestedAccuracyLevel',dbus.UInt32(8))
 props.Set('org.freedesktop.GeoClue2.Client','TimeThreshold',dbus.UInt32(1))
 client.connect_to_signal('LocationUpdated',changed)
 client.Start(timeout=45);result['started']=True;result['active']=bool(props.Get('org.freedesktop.GeoClue2.Client','Active'))
 GLib.timeout_add_seconds(int(sys.argv[1]),stop);loop.run()
except dbus.DBusException as error:
 result['error_name']=error.get_dbus_name();print(error.get_dbus_message(),file=sys.stderr)
finally:
 if result['started']:
  client.Stop(timeout=20);result['stopped']=True
 manager.DeleteClient(path,timeout=10);result['client_deleted']=True;bus.close()
print(json.dumps(result),flush=True)
