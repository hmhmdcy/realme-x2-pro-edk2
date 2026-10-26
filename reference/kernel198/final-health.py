from pathlib import Path
import dbus,hashlib,json,os,subprocess
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k198-final-health';out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k198-baseline/boot-id-private.txt').read_bytes();(out/'boot-id-private.txt').write_bytes(Path('/proc/sys/kernel/random/boot_id').read_bytes())
assert os.uname().version.startswith('#183 ') and Path('/proc/sys/kernel/tainted').read_text().strip()=='512'
names=['samurai_front_overlay','samurai_vio_phandle','samurai_pmic_fixture','qcom_pm8008','qcom_pm8008_regulator','v4l2_cci','imx471','samurai_cci_bringup','samurai_front_identify','i2c_qcom_cci'];assert all(not Path('/sys/module/'+n).exists() for n in names)
assert not Path('/sys/firmware/devicetree/base/samurai-vio-lookup').exists() and not Path('/sys/firmware/devicetree/base/soc@0/rsc@18200000/regulators-1/ldo1/phandle').exists()
front=json.loads((root/'k198-front-capture-r1/summary.json').read_text());assert front['normal_driver_bound'] and front['physical_id_accepted_by_normal_driver'] and front['physical_image_capture'] and front['pins_restored_exact'] and front['pmic_after_restore']==front['before']['pmic']
assert not Path('/sys/firmware/devicetree/base/samurai-front-restore').exists() and not Path('/sys/firmware/devicetree/base/soc@0/camss@acb3000/ports/port@2').exists()
assert Path('/sys/firmware/devicetree/base/soc@0/cci@ac4b000/status').read_bytes()==b'disabled\0'
assert all(not Path('/sys/bus/i2c/devices/1-'+f'{a:04x}').exists() for a in [4,5,8,9]) and not Path('/sys/bus/i2c/devices/i2c-6').exists() and not Path('/sys/bus/i2c/devices/i2c-7').exists()
assert not Path('/sys/firmware/devicetree/base/soc@0/geniqup@8c0000/i2c@890000/pmic@4').exists()
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')};assert all(v=='running' for v in rp.values())
bus=dbus.SystemBus(private=True);props=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties');power=int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState'));gps=int(props.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'));assert power==3 and gps==0
assert hashlib.sha256(Path('/usr/bin/ModemManager').read_bytes()).hexdigest()=='b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc'
proxy=dbus.Interface(bus.get_object('net.hadess.SensorProxy','/net/hadess/SensorProxy'),'org.freedesktop.DBus.Properties');has={n:bool(proxy.Get('net.hadess.SensorProxy',n)) for n in ['HasAccelerometer','HasAmbientLight','HasProximity']};assert all(has.values());bus.close()
assert (Path('/sys/bus/platform/devices/acb3000.camss')/'driver').resolve()==Path('/sys/bus/platform/drivers/qcom-camss')
module=Path(subprocess.check_output(['modinfo','-n','qcom-camss'],text=True).strip());assert hashlib.sha256(module.read_bytes()).hexdigest()=='e9b73f4c6bad90fbd6ff89ba45894c88b32b51bc9836ddd741ff56876eb13b0d'
assert not Path('/lib/firmware/samurai/k196-front.dtbo').exists()
assert not Path('/sys/kernel/tracing/instances/samurai-camera198').exists()
log=subprocess.check_output(['dmesg']);(out/'dmesg-private.txt').write_bytes(log);counts={k:log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()};assert counts==dict(warning=1,oops=0,gpu=0,slpi_fatal=0,bluetooth=1)
for n,path in [('clocks','/sys/kernel/debug/clk/clk_summary'),('regulators','/sys/kernel/debug/regulator/regulator_summary')]: (out/(n+'-private.txt')).write_bytes(Path(path).read_bytes())
reg=[]
for p in Path('/sys/class/regulator').glob('regulator.*'):
 if not (p/'name').is_file() or (p/'name').read_text().strip() not in ['ldo1','smps8']:continue
 node=p/'of_node'
 if not node.exists():node=p/'device/of_node'
 reg.append(dict(of_path=str(node.resolve()),name=(p/'name').read_text().strip(),values={n:(p/n).read_text().strip() for n in ['state','microvolts','num_users'] if (p/n).is_file()}))
assert any(r['of_path'].endswith('/regulators-1/ldo1') and r['values']==dict(state='disabled',microvolts='1800000',num_users='0') for r in reg)
assert any(r['name']=='smps8' and r['values']==dict(state='enabled',microvolts='1352000',num_users='3') for r in reg)
r=dict(stage=198,physical_frame_count=3,temporary_max_400mhz_experiment=True,frame_test_patterns_disabled=True,full_camera_function_not_yet_complete=True,original_camss_module_restored=True,original_camss_module_sha256=hashlib.sha256(module.read_bytes()).hexdigest(),kernel_build=183,same_boot_as189=True,uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),taint=512,fault_counts=counts,all_diagnostic_modules_unloaded=True,temporary_pmic_node_and_clients_removed=True,cci1_disabled=True,remoteprocs=rp,sensor_proxy=has,mm_power_state=power,location_enabled=gps,modemmanager191_unchanged=True,regulators=reg,physical_image_capture_proven=True,normal_imx471_probe_proven=True,camss_physical_graph_proven=True,production_max_clock_operation_unresolved=True,installed_modules_unchanged=True,reboot_or_flash_performed=False)
(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
