from pathlib import Path
import dbus, json, os, subprocess

root=Path('/var/lib/samurai');out=root/'k202-active-policy';assert not out.exists();out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k202-runtime/boot-id-private.txt').read_bytes()
bus=dbus.SystemBus(private=True)
mm=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties')
nm=dbus.Interface(bus.get_object('org.freedesktop.NetworkManager','/org/freedesktop/NetworkManager'),'org.freedesktop.DBus.Properties')
settings={name:bool(nm.Get('org.freedesktop.NetworkManager',name)) for name in ['WirelessEnabled','WirelessHardwareEnabled','WwanEnabled','WwanHardwareEnabled']}
rfkill=[]
for item in Path('/sys/class/rfkill').glob('rfkill*'):
 rfkill.append({key:(item/key).read_text().strip() for key in ['type','soft','hard']})
watch=json.loads((root/'gnss-assist/watch-state.json').read_text());(out/'watch-private.json').write_text(json.dumps(watch,indent=2)+'\n')
deps={}
for name in ['python3','py3-dbus','py3-gobject3','libqmi','libqrtr-glib','chrony','ca-certificates','modemmanager','modemmanager-openrc']:
 p=subprocess.run(['apk','info','-e',name],capture_output=True,text=True,timeout=10);deps[name]=p.returncode==0
pid=int(Path('/run/samurai-gnss-assist.pid').read_text());stat=Path('/proc/%d/stat'%pid).read_text().split(') ',1)[1].split();start=float(stat[19])/os.sysconf('SC_CLK_TCK')
report=dict(stage=202,same_new_boot=True,gps_enabled=int(mm.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled')),modem_power_state=int(mm.Get('org.freedesktop.ModemManager1.Modem','PowerState')),networkmanager_radio_preferences=settings,rfkill=rfkill,watch_running=watch['running'],watch_active=watch['active'],worker_starts=watch['worker_starts'],worker_completions=watch['worker_completions'],worker_result=watch['last_result'],watcher_start_uptime_seconds=start,installed_dependencies=deps)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');bus.close();print(json.dumps(report))
