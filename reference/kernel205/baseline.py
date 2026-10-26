from pathlib import Path
import dbus,hashlib,json,os,subprocess

os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k205-baseline';assert not out.exists();out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(root/'k204r2-runtime/boot-id-private.txt').read_bytes();(out/'boot-id-private.txt').write_bytes(boot)
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and os.uname().version.startswith('#183 ')
module=Path('/usr/lib/modules')/os.uname().release/'kernel/drivers/bluetooth/hci_uart.ko';digest=hashlib.sha256(module.read_bytes()).hexdigest();assert digest=='f6c5ed3538270480a72cf4bf8b1339103417941930b0d8ecb941fd11d16d7020'
(out/'loaded-hci-uart-build-id-private').write_bytes(Path('/sys/module/hci_uart/notes/.note.gnu.build-id').read_bytes())
bus=dbus.SystemBus(private=True);m=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties');power=int(m.Get('org.freedesktop.ModemManager1.Modem','PowerState'));gps=int(m.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'));assert gps==0
objects=dbus.Interface(bus.get_object('org.bluez','/'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();adapters=[v['org.bluez.Adapter1'] for v in objects.values() if 'org.bluez.Adapter1' in v];assert len(adapters)==1 and not adapters[0]['Powered'] and not adapters[0]['Discovering'];assert not any(v.get('org.bluez.Device1',{}).get('Connected',False) for v in objects.values())
s=dbus.Interface(bus.get_object('net.hadess.SensorProxy','/net/hadess/SensorProxy'),'org.freedesktop.DBus.Properties');has={n:bool(s.Get('net.hadess.SensorProxy',n)) for n in ['HasAccelerometer','HasAmbientLight','HasProximity']};assert all(has.values());bus.close()
for name,cmd in [('dmesg',['dmesg']),('interrupts',['cat','/proc/interrupts']),('bluetooth-startup',['cat','/usr/sbin/samurai-bluetooth']),('bluetooth-init',['cat','/etc/init.d/samurai-bluetooth'])]:
 p=subprocess.run(cmd,capture_output=True,timeout=15);(out/(name+'-private.txt')).write_bytes(p.stdout+p.stderr)
log=(out/'dmesg-private.txt').read_bytes();faults={k:log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',bluetooth=b'Frame reassembly failed',slpi_fatal=b'fatal error received',gpu=b'gpu fault:').items()};assert not any(faults.values())
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')};assert all(v=='running' for v in rp.values())
watch=json.loads((root/'gnss-assist/watch-state.json').read_text());assert watch['running'] and not watch['active'] and watch['time_prepared'] and watch['worker_starts']==watch['worker_completions']==1
r=dict(stage=205,fresh_same204r2_boot_verified=True,uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),taint=0,fault_counts=faults,remoteprocs=rp,sensor_proxy=has,hci_uart185_sha256=digest,bluetooth_off_no_discovery_or_connections=True,uart_rx_wake_enabled=Path('/sys/bus/platform/devices/c8c000.serial/power/wakeup').read_text().strip()=='enabled',mm_power_state=power,gps_enabled=gps,helper_running_idle=True,no_transition_or_radio_change=True)
(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
