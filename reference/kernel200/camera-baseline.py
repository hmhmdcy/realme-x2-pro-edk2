from pathlib import Path
import dbus,hashlib,json,os,subprocess

os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k200-camera-baseline';assert not out.exists();out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(root/'k200-runtime/boot-id-private.txt').read_bytes();(out/'boot-id-private.txt').write_bytes(boot)
assert os.uname().version.startswith('#183 ') and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert Path('/sys/firmware/devicetree/base/soc@0/cci@ac4b000/status').read_bytes()==b'disabled\0'
assert all(not Path('/sys/module/'+n).exists() for n in ['qcom_pm8008','qcom_pm8008_regulator','samurai_pmic_fixture','imx471','v4l2_cci','samurai_cci_bringup','samurai_front_identify'])
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')};assert all(v=='running' for v in rp.values())
bus=dbus.SystemBus(private=True);props=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties');power=int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState'));gps=int(props.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'));assert gps==0
sensor=dbus.Interface(bus.get_object('net.hadess.SensorProxy','/net/hadess/SensorProxy'),'org.freedesktop.DBus.Properties');has={n:bool(sensor.Get('net.hadess.SensorProxy',n)) for n in ['HasAccelerometer','HasAmbientLight','HasProximity']};assert all(has.values());bus.close()
assert hashlib.sha256(Path('/usr/bin/ModemManager').read_bytes()).hexdigest()=='b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc'
log=subprocess.check_output(['dmesg']);(out/'dmesg-private.txt').write_bytes(log)
counts={k:log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()};assert not any(counts.values())
r=dict(stage=200,kernel_build=183,new_static_dt_boot=True,taint=0,fault_counts=counts,remoteprocs=rp,sensor_proxy=has,mm_power_state=power,location_enabled=gps)
(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
