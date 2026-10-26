from pathlib import Path
import importlib.util,json

here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel205/reboot-r2')
spec=importlib.util.spec_from_file_location('new_usb',here.parent.parent/'kernel188/host.py');transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport);transport.PRIVATE=private
native=r'''
from pathlib import Path
import dbus,json,subprocess
root=Path('/var/lib/samurai');out=root/'k205r2-runtime'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(out/'boot-id-private.txt').read_bytes()
assert (out/'boot-id-private.txt').read_bytes()!=(root/'k205r2-before-reboot/boot-id-private.txt').read_bytes()
watch=json.loads((root/'gnss-assist/watch-state.json').read_text());(out/'pending-watch-private.json').write_text(json.dumps(watch,indent=2)+'\n')
for name,command in [('chrony-pending',['chronyc','tracking']),('wifi-pending',['iw','dev','wlan0','link']),('interrupts-pending',['cat','/proc/interrupts']),('dmesg-pending',['dmesg'])]:
 p=subprocess.run(command,capture_output=True,timeout=10);(out/(name+'-private.txt')).write_bytes(p.stdout+p.stderr)
bus=dbus.SystemBus(private=True);m=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties');power=int(m.Get('org.freedesktop.ModemManager1.Modem','PowerState'));gps=int(m.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'));bus.close()
clock=(out/'chrony-pending-private.txt').read_text();wifi=(out/'wifi-pending-private.txt').read_text();log=(out/'dmesg-pending-private.txt').read_bytes()
print(json.dumps(dict(stage=205,new_boot_verified=True,uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),taint=int(Path('/proc/sys/kernel/tainted').read_text()),uart_wakeup=Path('/sys/bus/platform/devices/c8c000.serial/power/wakeup').read_text().strip(),time_prepared=watch['time_prepared'],preparation_starts=watch['time_preparation_starts'],preparation_completions=watch['time_preparation_completions'],last_status=watch.get('time_preparation_last_result',{}).get('status'),last_result=watch.get('time_preparation_last_result'),clock_normal='Normal' in clock,wifi_connected='Connected to' in wifi,mm_power=power,gps=gps,faults={k:log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',bluetooth=b'Frame reassembly failed',slpi_fatal=b'fatal error received').items()})))
'''
p=transport.ssh('python3 -',input=native.encode(),timeout=45);(private/'pending-native-private.log').write_bytes(p.stdout+p.stderr);print(p.stdout.decode())
