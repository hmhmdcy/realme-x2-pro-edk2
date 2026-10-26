from pathlib import Path
import dbus,hashlib,json,os,runpy,subprocess,time

root=Path('/var/lib/samurai');out=root/'k204r2-final-health-r3';assert not out.exists();out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(root/'k204r2-runtime/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0';before=root/'k204r2-before-reboot'
for label in ['partition','userspace']:
 subprocess.run(['sha256sum','-c',str(before/(label+'-check.sha256'))],check=True,stdout=(out/(label+'-check-private.log')).open('wb'))
subprocess.run(['sha256sum','-c',str(before/'module-tree.sha256')],cwd=Path('/usr/lib/modules')/os.uname().release,check=True,stdout=(out/'module-check-private.log').open('wb'))
subprocess.run(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'],check=True,stdout=(out/'nv-check-private.log').open('wb'))
subprocess.run(['rc-service','samurai-ssc','status'],check=True,stdout=(out/'ssc-status-private.log').open('wb'))
ssc=json.loads(Path('/run/samurai-ssc/state.json').read_text());assert ssc['started'] and not ssc.get('stopped') and 'readiness_failure' not in ssc
ready={}
for name,label in [('accelerometer','Accelerometer'),('light','Light')]:
 p=Path('/run/samurai-ssc')/(name+'-readiness-private.log');raw=p.read_bytes();(out/p.name).write_bytes(raw)
 text=raw.decode(errors='replace');count=text.count(label+' sensor measurement:');disabled=(label+' sensor disabled').lower() in text.lower();assert count>0 and disabled;ready[name]=dict(measurements=count,clean_disable=True)
bus=dbus.SystemBus(private=True);obj=bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0');props=dbus.Interface(obj,'org.freedesktop.DBus.Properties');m=props.GetAll('org.freedesktop.ModemManager1.Modem');loc=props.GetAll('org.freedesktop.ModemManager1.Modem.Location');assert int(loc['Enabled'])==0 and int(m['PowerState'])==1 and not m['Bearers']
late_state=dict(gps_enabled=int(loc['Enabled']),signals_location=bool(loc['SignalsLocation']),refresh_rate=int(loc['GpsRefreshRate']),geoclue_owned=bus.name_has_owner('org.freedesktop.GeoClue2'))
(out/'late-location-state-private.json').write_text(json.dumps(late_state,indent=2)+'\n')
assert not late_state['geoclue_owned']
if late_state['signals_location'] or late_state['refresh_rate']!=30:
 api=dbus.Interface(obj,'org.freedesktop.ModemManager1.Modem.Location');api.Setup(dbus.UInt32(0),dbus.Boolean(False),timeout=20);api.SetGpsRefreshRate(dbus.UInt32(30),timeout=10);time.sleep(4)
loc=props.GetAll('org.freedesktop.ModemManager1.Modem.Location');assert int(loc['Enabled'])==0 and not loc['SignalsLocation'] and int(loc['GpsRefreshRate'])==30
sensor=dbus.Interface(bus.get_object('net.hadess.SensorProxy','/net/hadess/SensorProxy'),'org.freedesktop.DBus.Properties');has={n:bool(sensor.Get('net.hadess.SensorProxy',n)) for n in ['HasAccelerometer','HasAmbientLight','HasProximity']};assert all(has.values())
objects=dbus.Interface(bus.get_object('org.bluez','/'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();adapters=[v['org.bluez.Adapter1'] for v in objects.values() if 'org.bluez.Adapter1' in v];assert len(adapters)==1 and not adapters[0]['Powered'] and not adapters[0]['Discovering'];assert not any(v.get('org.bluez.Device1',{}).get('Connected',False) for v in objects.values());bus.close()
watch=json.loads((root/'gnss-assist/watch-state.json').read_text());assert watch['running'] and not watch['active'] and watch['time_prepared'] and watch['time_preparation_starts']==watch['time_preparation_completions']==3 and watch['worker_starts']==watch['worker_completions']==1
(out/'watch-state-private.json').write_text(json.dumps(watch,indent=2)+'\n');ns=runpy.run_path('/usr/sbin/samurai-gnss-assist',run_name='validity_readonly');valid=ns['loc_exchange']('validity');assert ns['validity_current'](valid['start'],valid['hours'],time.time());(out/'validity-private.json').write_text(json.dumps(valid,indent=2)+'\n')
uart=Path('/sys/bus/platform/devices/c8c000.serial');assert (uart/'power/wakeup').read_text().strip()=='enabled' and (uart/'of_node/pinctrl-names').read_bytes()==b'default\0sleep\0'
for name,command in [('pinctrl',['sh','-c','cat /sys/kernel/debug/pinctrl/*/pinmux-pins /sys/kernel/debug/pinctrl/*/pinconf-pins']),('interrupts',['cat','/proc/interrupts']),('wakeup-sources',['cat','/sys/kernel/debug/wakeup_sources']),('dmesg',['dmesg']),('wifi',['iw','dev','wlan0','link'])]:
 p=subprocess.run(command,capture_output=True,timeout=10);(out/(name+'-private.txt')).write_bytes(p.stdout+p.stderr);assert p.returncode==0
log=(out/'dmesg-private.txt').read_bytes();faults={k:log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()};assert not any(faults.values())
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')};assert all(v=='running' for v in rp.values())
manifest=json.loads((root/'packages/gnss-203/package-manifest.json').read_text())
for item in manifest['packages']:
 for name,expected in item['files'].items():
  p=Path('/')/name
  if expected['kind']=='symlink':assert p.is_symlink() and str(p.readlink())==expected['target']
  else:assert hashlib.sha256(p.read_bytes()).hexdigest()==expected['sha256'] and p.stat().st_mode & 0o7777==expected['mode']
assert Path('/sys/firmware/devicetree/base/soc@0/camss@acb3000/power-domain-names').read_bytes()==b'ife0\0ife1\0top\0mmcx\0'
for name in ['samurai_front_overlay','samurai_vio_phandle','samurai_cci_bringup','qcom_pm8008','imx471','i2c_qcom_cci']:assert not Path('/sys/module/'+name).exists()
test=json.loads((root/'k204r2-geoclue-first-session/summary.json').read_text());assert test['client_exit']==0 and test['gps_enabled_final']==0 and test['test_config_and_identity_removed'] and test['desktop_location_setting_restored']
assert Path('/etc/geoclue/geoclue.conf').read_bytes()==(root/'k204r2-geoclue-first-session/geoclue.conf-original-private').read_bytes()
report=dict(stage=204,reboot_cycle=2,same_verified_current_boot=True,uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),taint=0,fault_counts=faults,remoteprocs=rp,sensor_proxy=has,ssc_automatic_start_and_real_readiness_passed=True,ssc_readiness=ready,ssc_first_cycle_failure_not_reclassified=True,ssc_failure_diagnostic_source_sha256=hashlib.sha256(Path('/usr/sbin/samurai-ssc').read_bytes()).hexdigest(),uart_rx_wake_enabled=True,uart_sleep_state_present=True,uart_runtime_state=(uart/'power/runtime_status').read_text().strip(),bluetooth_off_no_scan_or_connections=True,bluetooth_first_cycle_phase5_not_fixed=True,bluetooth_pm_first_cycle_pass_does_not_prove_external_rx_wake=True,mm_power_state=int(m['PowerState']),mm_state=int(m['State']),mm_failed_reason=int(m['StateFailedReason']),gps_enabled=0,signals_location=False,gps_refresh_rate=30,helper_utc_preparation_attempts=3,helper_data_workers=1,current_assistance_independently_verified=True,validity_start=valid['start'],validity_hours=valid['hours'],all_apk203_payloads_still_exact=True,boot204_logdump183_persist_nv_modules_userspace_exact=True,camss_four_domains_and_no_camera_fixtures=True,wifi_connected='Connected to' in (out/'wifi-private.txt').read_text(),packaged_first_gnss_session_nmea_times=test['ggatime_distinct'],real_gnss_fix_obtained=bool(test['valid_gga'] or test['active_rmc'] or test['raw_fix_reports']),new_camera_capture_not_performed=True,second_cycle_no_flash=True)
report['late_location_state_before_normalization']=late_state;report['original_idle_location_settings_restored']=True
assert boot==Path('/proc/sys/kernel/random/boot_id').read_bytes();(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
