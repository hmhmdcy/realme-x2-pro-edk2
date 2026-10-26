from pathlib import Path
import dbus,hashlib,json,os,pwd,runpy,signal,subprocess,time

os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k202r2-final-health'
if out.exists():assert not list(out.iterdir())
else:out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(root/'k202r2-runtime/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ') and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
bus=dbus.SystemBus(private=True);obj=bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0');props=dbus.Interface(obj,'org.freedesktop.DBus.Properties');api=dbus.Interface(obj,'org.freedesktop.ModemManager1.Modem.Location')
assert int(props.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'))==0
idle_geoclue_retired=False
if bus.name_has_owner('org.freedesktop.GeoClue2'):
 manager=dbus.Interface(bus.get_object('org.freedesktop.GeoClue2','/org/freedesktop/GeoClue2/Manager'),'org.freedesktop.DBus.Properties')
 assert not bool(manager.Get('org.freedesktop.GeoClue2.Manager','InUse'))
 daemon=dbus.Interface(bus.get_object('org.freedesktop.DBus','/org/freedesktop/DBus'),'org.freedesktop.DBus');owner=daemon.GetNameOwner('org.freedesktop.GeoClue2');pid=int(daemon.GetConnectionUnixProcessID(owner))
 assert Path('/proc/%d/exe'%pid).resolve()==Path('/usr/libexec/geoclue')
 os.kill(pid,signal.SIGTERM)
 for unused in range(50):
  if not bus.name_has_owner('org.freedesktop.GeoClue2'):break
  time.sleep(.1)
 assert not bus.name_has_owner('org.freedesktop.GeoClue2');idle_geoclue_retired=True
previous=props.GetAll('org.freedesktop.ModemManager1.Modem.Location')
(out/'location-before-final-normalization-private.json').write_text(json.dumps(previous,default=int))
if previous['SignalsLocation'] or int(previous['GpsRefreshRate'])!=30:
 api.Setup(dbus.UInt32(0),dbus.Boolean(False),timeout=20);api.SetGpsRefreshRate(dbus.UInt32(30),timeout=10)
time.sleep(4)
loc=props.GetAll('org.freedesktop.ModemManager1.Modem.Location');m=props.GetAll('org.freedesktop.ModemManager1.Modem')
assert int(loc['Enabled'])==0 and not loc['SignalsLocation'] and int(loc['GpsRefreshRate'])==30
assert int(m['PowerState'])==1 and int(m['State'])==-1 and int(m['StateFailedReason'])==2 and not m['Bearers']
assert not bus.name_has_owner('org.freedesktop.GeoClue2')
sensor=dbus.Interface(bus.get_object('net.hadess.SensorProxy','/net/hadess/SensorProxy'),'org.freedesktop.DBus.Properties')
has={name:bool(sensor.Get('net.hadess.SensorProxy',name)) for name in ['HasAccelerometer','HasAmbientLight','HasProximity']};assert all(has.values());bus.close()
test=json.loads((root/'k202r2-geoclue-first-session/summary.json').read_text())
assert Path('/etc/geoclue/geoclue.conf').read_bytes()==(root/'k202r2-geoclue-first-session/geoclue.conf-original-private').read_bytes()
for path in ['/etc/geoclue/conf.d/99-samurai-gnss-test.conf','/usr/share/applications/org.realme.SamuraiGNSSValidation.desktop','/usr/libexec/samurai-gnss-validation']:assert not Path(path).exists()
user=pwd.getpwuid(10000)
def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(10000)
env={**os.environ,**json.loads((root/'k202r2-runtime/desktop-env-private.json').read_text()),'HOME':user.pw_dir}
p=subprocess.run(['gsettings','get','org.gnome.system.location','enabled'],preexec_fn=demote,env=env,capture_output=True,text=True,timeout=10);assert p.returncode==0 and p.stdout.strip()=='false'
for name in ['partition','userspace']:
 subprocess.run(['sha256sum','-c',str(root/('k202r2-before-reboot/'+name+'-check.sha256'))],check=True,stdout=(out/(name+'-check-private.txt')).open('wb'))
subprocess.run(['sha256sum','-c',str(root/'k202r2-before-reboot/module-tree.sha256')],cwd=Path('/usr/lib/modules')/os.uname().release,check=True,stdout=(out/'module-check-private.txt').open('wb'))
subprocess.run(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'],check=True,stdout=(out/'nv-check-private.txt').open('wb'))
helper=Path('/usr/sbin/samurai-gnss-assist');digest=hashlib.sha256(helper.read_bytes()).hexdigest();assert digest=='42168f33472d01dbf115ea766487c70d95332aabc8de02c25bdb381cea80af97'
watch=json.loads((root/'gnss-assist/watch-state.json').read_text());assert watch['running'] and not watch['active'] and watch['source_sha256']==digest
assert watch['worker_starts']==watch['worker_completions']==1 and watch['time_preparation_starts']==watch['time_preparation_completions']>=1 and watch['time_prepared']
(out/'watch-state-private.json').write_text(json.dumps(watch,indent=2)+'\n')
ns=runpy.run_path(str(helper),run_name='gnss_validity_readonly');validity=ns['loc_exchange']('validity');assert ns['validity_current'](validity['start'],validity['hours'],time.time())
(out/'independent-validity-private.json').write_text(json.dumps(validity,indent=2)+'\n')
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')};assert all(v=='running' for v in rp.values())
assert Path('/sys/bus/platform/devices/acb3000.camss/driver').resolve()==Path('/sys/bus/platform/drivers/qcom-camss')
assert Path('/sys/firmware/devicetree/base/soc@0/camss@acb3000/power-domain-names').read_bytes()==b'ife0\0ife1\0top\0mmcx\0'
for name in ['samurai_front_overlay','samurai_vio_phandle','samurai_cci_bringup','qcom_pm8008','imx471','i2c_qcom_cci']:assert not Path('/sys/module/'+name).exists()
log=subprocess.check_output(['dmesg']);(out/'dmesg-private.txt').write_bytes(log)
counts={k:log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()};assert not any(counts.values())
report=dict(stage=202,reboot_cycle=2,same_verified_new_boot=True,kernel_build=183,uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),taint=0,fault_counts=counts,remoteprocs=rp,sensor_proxy=has,helper_sha256=digest,openrc_autostart_and_idle_utc_preparation_verified=True,first_session_nmea_time_advances=test['ggatime_distinct']>0,first_session_nonzero_distinct_gga_times=test['ggatime_distinct'],first_session_real_fix_obtained=bool(test['valid_gga'] or test['active_rmc'] or test['raw_fix_reports'] or test.get('client',{}).get('valid_location_events',0)),current_assistance_independently_verified=True,validity_start=validity['start'],validity_hours=validity['hours'],mm_power_state=1,mm_state=-1,mm_failed_reason=2,bearers=0,gps_enabled=0,signals_location=False,gps_refresh_rate=30,desktop_location_setting_restored_false=True,temporary_test_policy_desktop_executable_removed=True,base_geoclue_configuration_unchanged=True,idle_geoclue_retired_after_test=idle_geoclue_retired,boot_logdump_persist_nv_module_tree_userspace_checks_pass=True,camss_four_domains_and_no_camera_fixtures=True,modem_power_or_reset_requests_sent=False,partition_flash_requests_sent=False)
assert boot==Path('/proc/sys/kernel/random/boot_id').read_bytes()
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
