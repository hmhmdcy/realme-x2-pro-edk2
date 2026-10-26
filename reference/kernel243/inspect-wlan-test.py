from pathlib import Path
import dbus,json
rows=[]
for p in Path('/sys/class/rfkill').glob('rfkill*'):
 rows.append({k:(p/k).read_text().strip() for k in ['name','type','soft','hard']}|dict(index=int(p.name[6:])))
bus=dbus.SystemBus(private=True);props=dbus.Interface(bus.get_object('org.freedesktop.NetworkManager','/org/freedesktop/NetworkManager'),'org.freedesktop.DBus.Properties')
radio={k:bool(props.Get('org.freedesktop.NetworkManager',k)) for k in ['WirelessEnabled','WirelessHardwareEnabled']};bus.close()
print(json.dumps(dict(stage=243,rfkill=rows,networkmanager=radio,readonly=True)))
