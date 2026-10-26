from pathlib import Path
import dbus,hashlib,json,os,struct,subprocess

os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k200-final-health';assert not out.exists();out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(root/'k200-runtime/boot-id-private.txt').read_bytes();(out/'boot-id-private.txt').write_bytes(boot)
assert os.uname().version.startswith('#183 ') and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
names=['samurai_camera_perf','samurai_front_overlay','samurai_vio_phandle','samurai_pmic_fixture','qcom_pm8008','qcom_pm8008_regulator','v4l2_cci','imx471','samurai_cci_bringup','samurai_front_identify','i2c_qcom_cci'];assert all(not Path('/sys/module/'+n).exists() for n in names)
dt=Path('/sys/firmware/devicetree/base');assert not (dt/'samurai-vio-lookup').exists() and not (dt/'soc@0/rsc@18200000/regulators-1/ldo1/phandle').exists()
assert not (dt/'samurai-front-restore').exists() and not (dt/'soc@0/camss@acb3000/ports/port@2').exists()
assert (dt/'soc@0/cci@ac4b000/status').read_bytes()==b'disabled\0'
assert (dt/'soc@0/camss@acb3000/power-domain-names').read_bytes()==b'ife0\0ife1\0top\0mmcx\0'
assert all(not Path('/sys/bus/i2c/devices/1-'+f'{a:04x}').exists() for a in [4,5,8,9]) and all(not Path('/sys/bus/i2c/devices/i2c-'+str(a)).exists() for a in [6,7])
assert not (dt/'soc@0/geniqup@8c0000/i2c@890000/pmic@4').exists() and not Path('/lib/firmware/samurai/k196-front.dtbo').exists()
front=json.loads((root/'k200-front-capture-r2/summary.json').read_text());assert front['physical_image_capture'] and front['pins_restored_exact'] and front['pmic_after_restore']==front['before']['pmic'] and not any(front['fault_delta'].values())
assert (Path('/sys/bus/platform/devices/acb3000.camss')/'driver').resolve()==Path('/sys/bus/platform/drivers/qcom-camss')
module_root=Path('/usr/lib/modules')/os.uname().release;loaded={}
for name,file in [('qcom_camss','kernel/drivers/media/platform/qcom/camss/qcom-camss.ko'),('hci_uart','kernel/drivers/bluetooth/hci_uart.ko'),('fastrpc','kernel/drivers/misc/fastrpc.ko')]:
 raw=(module_root/file).read_bytes();offset=struct.unpack_from('<Q',raw,40)[0];size,count,idx=struct.unpack_from('<HHH',raw,58);rows=[struct.unpack_from('<IIQQQQIIQQ',raw,offset+i*size) for i in range(count)];strings=raw[rows[idx][4]:rows[idx][4]+rows[idx][5]];note=next(r for r in rows if strings[r[0]:].split(b'\0',1)[0]==b'.note.gnu.build-id');assert Path('/sys/module/'+name+'/notes/.note.gnu.build-id').read_bytes()==raw[note[4]:note[4]+note[5]];loaded[name]=hashlib.sha256(raw).hexdigest()
assert loaded['qcom_camss']=='82cbc0528a76858ac57e149bdb540d14630112d74213384303960eead684fe58'
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')};assert all(v=='running' for v in rp.values())
bus=dbus.SystemBus(private=True);props=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties');power=int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState'));gps=int(props.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'));assert power==1 and gps==0
proxy=dbus.Interface(bus.get_object('net.hadess.SensorProxy','/net/hadess/SensorProxy'),'org.freedesktop.DBus.Properties');has={n:bool(proxy.Get('net.hadess.SensorProxy',n)) for n in ['HasAccelerometer','HasAmbientLight','HasProximity']};assert all(has.values());bus.close()
assert hashlib.sha256(Path('/usr/bin/ModemManager').read_bytes()).hexdigest()=='b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc'
log=subprocess.check_output(['dmesg']);(out/'dmesg-private.txt').write_bytes(log);counts={k:log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()};assert not any(counts.values())
for name,path in [('clocks','/sys/kernel/debug/clk/clk_summary'),('regulators','/sys/kernel/debug/regulator/regulator_summary'),('genpd','/sys/kernel/debug/pm_genpd/pm_genpd_summary')]:
 (out/(name+'-private.txt')).write_bytes(Path(path).read_bytes())
reg=[]
for p in Path('/sys/class/regulator').glob('regulator.*'):
 if not (p/'name').exists() or (p/'name').read_text().strip() not in ['ldo1','smps8']:continue
 node=p/'of_node'
 if not node.exists():node=p/'device/of_node'
 reg.append(dict(of_path=str(node.resolve()),name=(p/'name').read_text().strip(),values={n:(p/n).read_text().strip() for n in ['state','microvolts','num_users'] if (p/n).exists()}))
assert any(r['of_path'].endswith('/regulators-1/ldo1') and r['values']==dict(state='disabled',microvolts='1800000',num_users='0') for r in reg)
assert any(r['name']=='smps8' and r['values']==dict(state='enabled',microvolts='1352000',num_users='3') for r in reg)
r=dict(stage=200,new_static_dt_boot_verified=True,kernel_build=183,uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),taint=0,fault_counts=counts,all_diagnostic_modules_unloaded=True,temporary_pmic_and_sensor_nodes_removed=True,cci1_disabled=True,persistent_camss_candidate_and_four_domains_remain=True,loaded_build_ids_verified=loaded,remoteprocs=rp,sensor_proxy=has,mm_power_state=power,location_enabled=gps,modemmanager191_unchanged=True,regulators=reg,physical_frame_count=12,first_capture_cleanup_mismatch_separately_restored=True,final_capture_cleanup_exact=True,static_camera_sensor_and_pmic_dt_deployment_still_pending=True)
(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
