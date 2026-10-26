from pathlib import Path
import dbus,hashlib,json,os,subprocess
os.umask(0o077);out=Path('/var/lib/samurai/k193-baseline');out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==Path('/var/lib/samurai/k189r2-reboot-runtime/boot-id-private.txt').read_bytes();(out/'boot-id-private.txt').write_bytes(boot)
assert os.uname().version.startswith('#183 ')
tree=Path('/sys/firmware/devicetree/base');camera=tree/'soc@0/cci@ac4b000';assert camera.is_dir() and (camera/'status').read_bytes()==b'disabled\0'
assert all(not p.exists() for p in [Path('/sys/bus/platform/devices/ac4b000.cci'),Path('/sys/module/samurai_cci_bringup')])
def values(node):
 return {p.name:p.read_bytes().hex() for p in node.iterdir() if p.is_file()}
(out/'cci-node-properties-private.json').write_text(json.dumps(dict(controller=values(camera),children={p.name:values(p) for p in camera.iterdir() if p.is_dir()}),indent=2))
bus=dbus.SystemBus(private=True);props=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties')
power=int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState'));assert power==3 and int(props.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'))==0
assert hashlib.sha256(Path('/usr/bin/ModemManager').read_bytes()).hexdigest()=='b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc'
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')};assert all(v=='running' for v in rp.values())
log=subprocess.check_output(['dmesg'],text=True);(out/'dmesg-private.txt').write_text(log)
faults={k:log.count(v) for k,v in dict(warning='WARNING:',oops='Oops:',gpu='gpu fault:',slpi_fatal='fatal error received',bluetooth='Frame reassembly failed').items()}
proxy=dbus.Interface(bus.get_object('net.hadess.SensorProxy','/net/hadess/SensorProxy'),'org.freedesktop.DBus.Properties');sensors={n:bool(proxy.Get('net.hadess.SensorProxy',n)) for n in ['HasAccelerometer','HasAmbientLight','HasProximity']};assert all(sensors.values())
for path,name in [('/sys/kernel/debug/pinctrl/3100000.pinctrl/pinconf-pins','tlmm-pinconf-private.txt'),('/sys/kernel/debug/pinctrl/3100000.pinctrl/pinmux-pins','tlmm-pinmux-private.txt'),('/sys/kernel/debug/regulator/regulator_summary','regulator-summary-private.txt'),('/sys/kernel/debug/clk/clk_summary','clock-summary-private.txt')]:
 p=Path(path)
 if p.is_file():(out/name).write_bytes(p.read_bytes())
result=dict(stage=193,same_boot_as189=True,kernel_build=183,taint=int(Path('/proc/sys/kernel/tainted').read_text()),remoteprocs=rp,mm_power_state=power,sensor_proxy=sensors,fault_counts=faults,root_compatible=(tree/'compatible').read_bytes().rstrip(b'\0').decode().split('\0'),cci1_disabled=True,cci1_children=[p.name for p in camera.iterdir() if p.is_dir()],of_symbols_present=(tree/'__symbols__').exists())
assert result['taint']==0;(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');bus.close();print(json.dumps(result))
