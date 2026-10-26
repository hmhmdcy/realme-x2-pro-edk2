from pathlib import Path
import dbus,hashlib,json,subprocess

root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k200-runtime/boot-id-private.txt').read_bytes()
r=dict(services={},runlevels={},user10000_present=subprocess.run(['pgrep','-u','10000'],stdout=subprocess.DEVNULL).returncode==0)
for n in ['greetd','networkmanager','samurai-ssc','iio-sensor-proxy','bluetooth','modemmanager']:
 p=subprocess.run(['rc-service',n,'status'],capture_output=True);r['services'][n]=dict(running=p.returncode==0,status=(p.stdout+p.stderr).decode().strip())
 r['runlevels'][n]=[p.parent.name for p in Path('/etc/runlevels').glob('*/'+n)]
bus=dbus.SystemBus(private=True)
if bus.name_has_owner('org.freedesktop.ModemManager1'):
 objects=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
 r['modems']=[]
 for path,interfaces in objects.items():
  m=interfaces.get('org.freedesktop.ModemManager1.Modem')
  if m:r['modems'].append(dict(state=int(m['State']),power=int(m['PowerState']),gps_enabled=int(interfaces.get('org.freedesktop.ModemManager1.Modem.Location',{}).get('Enabled',0))))
r['sensor_proxy_owned']=bus.name_has_owner('net.hadess.SensorProxy');bus.close()
p=Path('/run/samurai-ssc/state.json')
if p.exists():
 state=json.loads(p.read_text());r['ssc_state']={k:state[k] for k in ['started','attempted','stopped','reason'] if k in state}
nm=subprocess.run(['nmcli','-t','-f','DEVICE,STATE','device'],capture_output=True,text=True);r['network_device_states']=nm.stdout.splitlines()
r['uptime_seconds']=float(Path('/proc/uptime').read_text().split()[0]);print(json.dumps(r))
