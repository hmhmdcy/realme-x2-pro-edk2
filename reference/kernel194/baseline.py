from pathlib import Path
import dbus,hashlib,json,os,subprocess
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k194-baseline';out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(root/'k189r2-reboot-runtime/boot-id-private.txt').read_bytes();(out/'boot-id-private.txt').write_bytes(boot)
assert os.uname().version.startswith('#183 ') and Path('/proc/sys/kernel/tainted').read_text().strip()=='512'
assert Path('/sys/firmware/devicetree/base/soc@0/cci@ac4b000/status').read_bytes()==b'disabled\0'
assert not Path('/sys/module/samurai_cci_bringup').exists() and not Path('/sys/module/samurai_front_identify').exists()
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')};assert all(v=='running' for v in rp.values())
bus=dbus.SystemBus(private=True);props=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties');assert int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState'))==3 and int(props.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'))==0
assert hashlib.sha256(Path('/usr/bin/ModemManager').read_bytes()).hexdigest()=='b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc'
sensor=dbus.Interface(bus.get_object('net.hadess.SensorProxy','/net/hadess/SensorProxy'),'org.freedesktop.DBus.Properties');has={n:bool(sensor.Get('net.hadess.SensorProxy',n)) for n in ['HasAccelerometer','HasAmbientLight','HasProximity']};assert all(has.values());bus.close()
log=subprocess.check_output(['dmesg']);(out/'dmesg-private.txt').write_bytes(log);counts={k:log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()};assert counts==dict(warning=1,oops=0,gpu=0,slpi_fatal=0,bluetooth=1)
report=dict(stage=194,same_boot_as189=True,kernel_build=183,taint=512,remoteprocs=rp,sensor_proxy=has,mm_power_state=3,location_enabled=0,fault_counts=counts,diagnostic_modules_unloaded=True,cci1_disabled=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
