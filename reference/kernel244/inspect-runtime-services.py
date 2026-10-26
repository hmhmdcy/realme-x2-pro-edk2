from pathlib import Path
import dbus,json,subprocess,time
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k244-runtime/boot-id-private.txt').read_bytes()
bus=dbus.SystemBus(private=True);nm=bus.get_object('org.freedesktop.NetworkManager','/org/freedesktop/NetworkManager');devices=[]
for path in dbus.Interface(nm,'org.freedesktop.NetworkManager').GetDevices():
 v=dbus.Interface(bus.get_object('org.freedesktop.NetworkManager',str(path)),'org.freedesktop.DBus.Properties').GetAll('org.freedesktop.NetworkManager.Device');devices.append(dict(type=int(v['DeviceType']),state=int(v['State'])))
bus.close();watch=json.loads((r/'gnss-assist/watch-state.json').read_text());x=subprocess.run(['chronyc','tracking'],capture_output=True,timeout=10)
report=dict(stage=244,networkmanager_devices=devices,assist={k:watch.get(k) for k in ['running','active','time_prepared','time_preparation_starts','time_preparation_completions','worker_starts','worker_completions','state','last_error']},system_utc=time.strftime('%Y-%m-%d %H:%M:%S',time.gmtime()),chrony_exit=x.returncode)
print(json.dumps({'report':report,'private':{'watch':watch,'chrony':(x.stdout+x.stderr).decode(),'services':subprocess.run(['rc-status','-a'],capture_output=True).stdout.decode()}}))
