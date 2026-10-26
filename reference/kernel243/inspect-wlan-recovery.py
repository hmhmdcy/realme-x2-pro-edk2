from pathlib import Path
import dbus,json
bus=dbus.SystemBus(private=True);nm=bus.get_object('org.freedesktop.NetworkManager','/org/freedesktop/NetworkManager');props=dbus.Interface(nm,'org.freedesktop.DBus.Properties');states=[];private=[]
for path in dbus.Interface(nm,'org.freedesktop.NetworkManager').GetDevices():
 v=dbus.Interface(bus.get_object('org.freedesktop.NetworkManager',str(path)),'org.freedesktop.DBus.Properties').GetAll('org.freedesktop.NetworkManager.Device')
 states.append(dict(type=int(v['DeviceType']),state=int(v['State']),reason=[int(x) for x in v['StateReason']],managed=bool(v['Managed']),autoconnect=bool(v['Autoconnect'])))
 private.append(dict(path=str(path),interface=str(v['Interface']),active=str(v['ActiveConnection'])))
report=dict(stage=243,radio={k:bool(props.Get('org.freedesktop.NetworkManager',k)) for k in ['WirelessEnabled','WirelessHardwareEnabled']},devices=states,rfkill={p.name:{k:(p/k).read_text().strip() for k in ['type','soft','hard']} for p in Path('/sys/class/rfkill').glob('rfkill*')})
bus.close();print(json.dumps({'report':report,'private':private}))
