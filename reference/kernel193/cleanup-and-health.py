from pathlib import Path
import dbus,hashlib,json,os,subprocess
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k193-final-health';out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(root/'k193-baseline/boot-id-private.txt').read_bytes();(out/'boot-id-private.txt').write_bytes(boot)
prior=json.loads((root/'k193-front-identify-r3/summary.json').read_text());assert prior['module_parameters']==dict(sensor_id=0x471,restore_result=0,ready_samples=2,sequence_result=0) and prior['gpio_directions_and_levels_restored'] and prior['pmic_entire_sample_restored']
current={p.name:int(p.read_text()) for p in Path('/sys/module/samurai_front_identify/parameters').iterdir()};assert current==prior['module_parameters']
def command(args,name):
 p=subprocess.run(args,capture_output=True,timeout=15);(out/(name+'-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0,name
command(['rmmod','samurai_front_identify'],'unload-front-helper');assert not Path('/sys/module/samurai_front_identify').exists()
command(['rmmod','samurai_cci_bringup'],'unload-cci-helper');assert not Path('/sys/module/samurai_cci_bringup').exists()
assert Path('/sys/firmware/devicetree/base/soc@0/cci@ac4b000/status').read_bytes()==b'disabled\0'
assert not Path('/sys/bus/platform/devices/ac4b000.cci').exists() and not Path('/sys/bus/i2c/devices/i2c-6').exists() and not Path('/sys/bus/i2c/devices/i2c-7').exists()
load=json.loads((root/'k193-cci-load/summary.json').read_text());assert load['cci_driver_preloaded'] is False
command(['modprobe','-r','i2c-qcom-cci'],'unload-previously-absent-driver');assert not Path('/sys/module/i2c_qcom_cci').exists()
assert all(not Path('/sys/bus/i2c/devices/1-'+f'{a:04x}').exists() for a in [4,5])
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')};assert all(v=='running' for v in rp.values())
bus=dbus.SystemBus(private=True);props=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties')
power=int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState'));gps=int(props.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'));assert power==3 and gps==0
assert hashlib.sha256(Path('/usr/bin/ModemManager').read_bytes()).hexdigest()=='b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc'
proxy=dbus.Interface(bus.get_object('net.hadess.SensorProxy','/net/hadess/SensorProxy'),'org.freedesktop.DBus.Properties');has={n:bool(proxy.Get('net.hadess.SensorProxy',n)) for n in ['HasAccelerometer','HasAmbientLight','HasProximity']};assert all(has.values());bus.close()
reg=[]
for p in Path('/sys/class/regulator').glob('regulator.*'):
 if not (p/'name').is_file() or (p/'name').read_text().strip() not in ['ldo1','smps8']:continue
 node=p/'of_node'
 if not node.exists():node=p/'device/of_node'
 reg.append(dict(of_path=str(node.resolve()),name=(p/'name').read_text().strip(),values={n:(p/n).read_text().strip() for n in ['state','microvolts','num_users'] if (p/n).is_file()}))
assert any(r['of_path'].endswith('/regulators-1/ldo1') and r['values']['microvolts']=='1800000' and r['values']['num_users']=='0' and r['values']['state']=='disabled' for r in reg)
assert any(r['name']=='smps8' and r['values']==dict(state='enabled',microvolts='1352000',num_users='3') for r in reg)
assert any(r['of_path'].endswith('/regulators-0/ldo1') and r['values']==dict(state='enabled',microvolts='752000',num_users='1') for r in reg)
log=subprocess.check_output(['dmesg']);(out/'dmesg-private.txt').write_bytes(log)
counts={k:log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()};assert counts==dict(warning=1,oops=0,gpu=0,slpi_fatal=0,bluetooth=1)
assert int(Path('/proc/sys/kernel/tainted').read_text())==512
(out/'clocks-private.txt').write_bytes(Path('/sys/kernel/debug/clk/clk_summary').read_bytes());(out/'regulators-private.txt').write_bytes(Path('/sys/kernel/debug/regulator/regulator_summary').read_bytes())
report=dict(stage=193,same_boot_as189=True,uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),taint=512,taint_cause='r2 MCLK2 enable attempted while TITAN_TOP_GDSC was off; warning preserved',fault_counts=counts,physical_front_sensor_id=0x471,physical_sensor_identity_proven=True,physical_image_capture_proven=False,all_diagnostic_modules_unloaded=True,cci1_status_restored_disabled=True,temporary_i2c_adapters_and_clients_removed=True,remoteprocs=rp,sensor_proxy=has,mm_power_state=power,location_enabled=gps,modemmanager191_unchanged=True,regulators=reg,pmic_programmed_register_sample_restored=True,physical_gpio_directions_and_levels_restored=True,voltage_or_gpio_persistent_override=False)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
