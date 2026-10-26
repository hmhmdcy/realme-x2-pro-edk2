from pathlib import Path
import dbus,hashlib,json,os,shutil,subprocess
os.umask(0o077)
out=Path('/var/lib/samurai/k192-baseline');out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k189r2-reboot-runtime/boot-id-private.txt').read_bytes()
bus=dbus.SystemBus(private=True);obj=bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0');props=dbus.Interface(obj,'org.freedesktop.DBus.Properties')
assert int(props.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'))==0
assert int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState'))==3
assert hashlib.sha256(Path('/usr/bin/ModemManager').read_bytes()).hexdigest()=='b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc'
for path,name in [('/sys/kernel/debug/regulator/regulator_summary','regulators-private.txt'),('/sys/kernel/debug/gpio','gpio-private.txt'),('/sys/kernel/debug/clk/clk_summary','clocks-private.txt')]:
 p=Path(path);assert p.is_file();(out/name).write_bytes(p.read_bytes())
i2c=[]
for p in Path('/sys/class/i2c-adapter').glob('i2c-*'):
 of=p/'device/of_node'
 if not of.exists():of=p/'of_node'
 adapter=dict(bus=p.name,name=(p/'name').read_text().strip(),of_path=str(of.resolve()) if of.exists() else None)
 bus_number=p.name.split('-')[1];adapter['clients']=[dict(name=c.name,driver=str((c/'driver').resolve()) if (c/'driver').exists() else None) for c in Path('/sys/bus/i2c/devices').glob(bus_number+'-*')]
 i2c.append(adapter)
(out/'i2c-private.json').write_text(json.dumps(i2c,indent=2))
log=subprocess.check_output(['dmesg'],text=True);(out/'dmesg-private.txt').write_text(log)
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')};assert all(v=='running' for v in rp.values())
report=dict(stage=192,same_boot_as189=True,kernel_build=183,taint=int(Path('/proc/sys/kernel/tainted').read_text()),remoteprocs=rp,mm_power_state=3,
 tools={name:shutil.which(name) for name in ['i2ctransfer','i2cget','gpioinfo','gpioget','gpioset','gpiodetect']},adapters=i2c,
 fault_counts={k:log.count(v) for k,v in dict(warning='WARNING:',oops='Oops:',gpu='gpu fault:',slpi_fatal='fatal error received',bluetooth='Frame reassembly failed').items()})
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');bus.close();print(json.dumps(report))
