from pathlib import Path
import dbus,hashlib,json,os,subprocess

os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k204-baseline-r2';assert not out.exists();out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(root/'k203-baseline/boot-id-private.txt').read_bytes();(out/'boot-id-private.txt').write_bytes(boot)
assert os.uname().version.startswith('#183 ') and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
prior=json.loads((root/'k203-package-preflight/processes-private.json').read_text())
assert hashlib.sha256(Path('/proc/%d/exe'%prior['mm_pid']).read_bytes()).hexdigest()=='b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc'
bus=dbus.SystemBus(private=True);daemon=dbus.Interface(bus.get_object('org.freedesktop.DBus','/org/freedesktop/DBus'),'org.freedesktop.DBus')
props=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties');m=props.GetAll('org.freedesktop.ModemManager1.Modem');loc=props.GetAll('org.freedesktop.ModemManager1.Modem.Location');assert int(loc['Enabled'])==0
objects=dbus.Interface(bus.get_object('org.bluez','/'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
adapters=[dict(powered=bool(v['org.bluez.Adapter1']['Powered']),discovering=bool(v['org.bluez.Adapter1']['Discovering']),pairable=bool(v['org.bluez.Adapter1']['Pairable'])) for v in objects.values() if 'org.bluez.Adapter1' in v]
connected=sum(bool(v['org.bluez.Device1'].get('Connected')) for v in objects.values() if 'org.bluez.Device1' in v)
assert connected==0 and all(not a['discovering'] for a in adapters)
bus.close();(out/'mm-state-private.json').write_text(json.dumps({k:str(v) for k,v in m.items()},indent=2)+'\n')
details={}
for p in [Path('/sys/bus/platform/devices/c8c000.serial'),Path('/sys/bus/serial/devices/serial0-0'),Path('/sys/class/bluetooth/hci0')]:
 if not p.exists():continue
 r={}
 for n in ['power/wakeup','power/control','power/runtime_status','power/runtime_active_time','power/runtime_suspended_time']:
  f=p/n
  if f.is_file():r[n]=f.read_text().strip()
 r['path']=str(p.resolve());details[str(p)]=r
(out/'uart-pm-private.json').write_text(json.dumps(details,indent=2)+'\n')
for name,command in [('dmesg',['dmesg']),('interrupts',['cat','/proc/interrupts']),('wakeup-sources',['cat','/sys/kernel/debug/wakeup_sources']),('pinctrl',['sh','-c','cat /sys/kernel/debug/pinctrl/*/pinmux-pins /sys/kernel/debug/pinctrl/*/pinconf-pins']),('bluetooth-init',['cat','/etc/init.d/samurai-bluetooth'])]:
 p=subprocess.run(command,capture_output=True,timeout=30);(out/(name+'-private.txt')).write_bytes(p.stdout+p.stderr)
fdt=Path('/sys/firmware/fdt');assert fdt.is_file();(out/'live-private.dtb').write_bytes(fdt.read_bytes())
log=(out/'dmesg-private.txt').read_bytes();faults={k:log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()}
watch=json.loads((root/'gnss-assist/watch-state.json').read_text());rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')}
report=dict(stage=204,fresh_same203_boot_verified=True,kernel_build=183,uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),taint=int(Path('/proc/sys/kernel/tainted').read_text()),fault_counts=faults,mm_loaded191_hash_verified=True,mm_power_state=int(m['PowerState']),mm_state=int(m['State']),gps_enabled=int(loc['Enabled']),helper_running_idle=watch['running'] and not watch['active'],bluetooth_adapters=adapters,bluetooth_connections=connected,remoteprocs=rp,uart_platform_wakeup_exposed=bool(details.get('/sys/bus/platform/devices/c8c000.serial',{}).get('power/wakeup')),no_transition_or_radio_change=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
