from pathlib import Path
import configparser,dbus,hashlib,json,math,os,pwd,signal,subprocess,time

os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k206-geoclue-first-session';assert not out.exists();out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k206-gnss-context/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
watch_before=json.loads((root/'gnss-assist/watch-state.json').read_text());assert watch_before['running'] and not watch_before['active'] and watch_before['worker_starts']==watch_before['worker_completions']==0
assert watch_before['time_prepared'] and watch_before['time_preparation_starts']==watch_before['time_preparation_completions']>=1
(out/'watch-before-private.json').write_text(json.dumps(watch_before))
bus=dbus.SystemBus(private=True);assert not bus.name_has_owner('org.freedesktop.GeoClue2')
daemon=dbus.Interface(bus.get_object('org.freedesktop.DBus','/org/freedesktop/DBus'),'org.freedesktop.DBus')
mmobj=bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0');mp=dbus.Interface(mmobj,'org.freedesktop.DBus.Properties');api=dbus.Interface(mmobj,'org.freedesktop.ModemManager1.Modem.Location')
old=mp.GetAll('org.freedesktop.ModemManager1.Modem.Location');assert int(old['Enabled'])==0
base=Path('/etc/geoclue/geoclue.conf');original=base.read_bytes();(out/'geoclue.conf-original-private').write_bytes(original)
config=configparser.ConfigParser(interpolation=None,strict=False);config.read_string(original.decode())
for section in ['ip','wifi','3g','cdma','network-nmea','static-source']:config[section]['enable']='false'
config['modem-gps']['enable']='true';config['wifi']['submit-data']='false'
config['org.realme.SamuraiGNSSValidation']={'allowed':'true','system':'false','users':'10000;'}
drop=Path('/etc/geoclue/conf.d/99-samurai-gnss-test.conf');assert not drop.exists();drop.parent.mkdir(mode=0o755,exist_ok=True);assert drop.parent.stat().st_mode & 0o777 == 0o755
desktop=Path('/usr/share/applications/org.realme.SamuraiGNSSValidation.desktop');assert not desktop.exists()
script=Path('/usr/libexec/samurai-gnss-validation');assert script.exists()
report=dict(stage=206,new_boot_verified=True,first_session_after_automatic_idle_utc=True,tftp_runtime_replaced_before_session=True,new_tftp_startup_not_yet_tested=True,idle_utc_preparation=watch_before['time_preparation_last_result'],idle_utc_preparation_attempts=watch_before['time_preparation_starts'],manual_utc_or_data_injection=False,ggatime_nonzero=0,ggatime_distinct=0,automatic_worker_observed=False,initial_modem_power_state=int(mp.Get('org.freedesktop.ModemManager1.Modem','PowerState')),gnss_only_geoclue_test=True,other_location_sources_disabled_for_test=True,client_uid=10000,distinct_installed_desktop_identity=True,gps_enabled_observed=False,valid_gga=0,active_rmc=0,raw_fix_reports=0,positive_cnr_fields=0,unique_nmea=0,nmea_types={},checksum_failures=0,locations=0)
beforelog=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(beforelog)
child=None;geopid=None;seen=set();ggatimes=set();started=time.monotonic()
user=pwd.getpwuid(10000)
def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(10000)
desktop_env={**os.environ,**json.loads((root/'k206-gnss-context/desktop-env-private.json').read_text()),'HOME':user.pw_dir}
def setting(value=None):
 args=['gsettings','get' if value is None else 'set','org.gnome.system.location','enabled']
 if value is not None:args.append('true' if value else 'false')
 p=subprocess.run(args,preexec_fn=demote,env=desktop_env,capture_output=True,text=True,timeout=10);assert p.returncode==0
 if value is None:assert p.stdout.strip() in ['true','false'];return p.stdout.strip()=='true'
old_desktop_location=setting();report['desktop_location_before']=old_desktop_location
def parse(values):
 for key,value in values.items():
  if int(key)==2 and isinstance(value,dict) and all(n in value and math.isfinite(float(value[n])) for n in ['latitude','longitude']):report['raw_fix_reports']+=1
  if int(key)!=4:continue
  for sentence in str(value).replace('\r','').split('\n'):
   if not sentence.startswith('$') or sentence in seen:continue
   seen.add(sentence);report['unique_nmea']+=1
   if '*' not in sentence:report['checksum_failures']+=1;continue
   body,check=sentence[1:].split('*',1);checksum=0
   for character in body:checksum^=ord(character)
   try:valid=checksum==int(check[:2],16)
   except ValueError:valid=False
   if not valid:report['checksum_failures']+=1;continue
   fields=body.split(',');name=fields[0];report['nmea_types'][name]=report['nmea_types'].get(name,0)+1;kind=name[-3:]
   if kind=='GGA' and len(fields)>1 and fields[1] not in ['', '0', '000000', '000000.0', '000000.00']:
    ggatimes.add(fields[1]);report['ggatime_nonzero']+=1;report['ggatime_distinct']=len(ggatimes)
   if kind=='GGA' and len(fields)>6 and fields[6].isdigit() and int(fields[6])>0:report['valid_gga']+=1
   if kind=='RMC' and len(fields)>2 and fields[2]=='A':report['active_rmc']+=1
   if kind=='GSV':
    for i in range(7,len(fields),4):
     try:cnr=float(fields[i])
     except ValueError:continue
     report['positive_cnr_fields']+=int(math.isfinite(cnr) and cnr>0)

try:
 with drop.open('x') as f:config.write(f)
 os.chmod(drop,0o644)
 desktop.write_text('[Desktop Entry]\nType=Application\nName=Samurai GNSS Validation\nExec=/usr/bin/python3 /usr/libexec/samurai-gnss-validation 180\nNoDisplay=true\n');os.chmod(desktop,0o644)
 if not old_desktop_location:setting(True)
 assert setting();time.sleep(1)
 child=subprocess.Popen(['/usr/bin/python3',str(script),'180'],stdout=(out/'client-result-private.json').open('wb'),stderr=(out/'client-errors-private.txt').open('wb'),preexec_fn=demote,env=desktop_env)
 deadline=time.monotonic()+235
 with (out/'locations-private.jsonl').open('x') as stream:
  while child.poll() is None and time.monotonic()<deadline:
   if bus.name_has_owner('org.freedesktop.GeoClue2'):
    owner=daemon.GetNameOwner('org.freedesktop.GeoClue2');geopid=int(daemon.GetConnectionUnixProcessID(owner))
   enabled=int(mp.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'));report['gps_enabled_observed']|=bool(enabled&6)
   values=api.GetLocation(timeout=8);stream.write(json.dumps(dict(elapsed=time.monotonic()-started,locations=values),default=str)+'\n');stream.flush();parse(values)
   watch_now=json.loads((root/'gnss-assist/watch-state.json').read_text());report['automatic_worker_observed']|=watch_now['worker_starts']>0
   (out/'watch-latest-private.json').write_text(json.dumps(watch_now))
   (out/'progress.json').write_text(json.dumps(report,indent=2)+'\n');time.sleep(1)
 if child.poll() is None:report['deadline']=True;child.terminate();child.wait(timeout=25)
 report['client_exit']=child.returncode
 result=out/'client-result-private.json'
 if result.stat().st_size:report['client']=json.loads(result.read_text())
finally:
 if child is not None and child.poll() is None:child.terminate();child.wait(timeout=25)
 if bus.name_has_owner('org.freedesktop.GeoClue2'):
  obj=bus.get_object('org.freedesktop.GeoClue2','/org/freedesktop/GeoClue2/Manager');inuse=bool(dbus.Interface(obj,'org.freedesktop.DBus.Properties').Get('org.freedesktop.GeoClue2.Manager','InUse'));assert not inuse
  current=int(daemon.GetConnectionUnixProcessID(daemon.GetNameOwner('org.freedesktop.GeoClue2')))
  assert (geopid is None or geopid==current) and (Path('/proc')/str(current)/'exe').resolve()==Path('/usr/libexec/geoclue')
  os.kill(current,signal.SIGTERM)
  for unused in range(30):
   if not bus.name_has_owner('org.freedesktop.GeoClue2'):break
   time.sleep(.1)
  assert not bus.name_has_owner('org.freedesktop.GeoClue2')
 assert int(mp.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'))==0
 api.Setup(dbus.UInt32(0),dbus.Boolean(bool(old['SignalsLocation'])),timeout=25)
 api.SetGpsRefreshRate(dbus.UInt32(int(old['GpsRefreshRate'])),timeout=10)
 if drop.exists():drop.unlink()
 if desktop.exists():desktop.unlink()
 if script.exists():script.unlink()
 setting(old_desktop_location);report['desktop_location_setting_restored']=setting()==old_desktop_location
 assert base.read_bytes()==original
 report['test_config_and_identity_removed']=not drop.exists() and not desktop.exists();report['normal_geoclue_permissions_restored']=True
 report['gps_enabled_final']=int(mp.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'));report['signals_location_restored']=bool(mp.Get('org.freedesktop.ModemManager1.Modem.Location','SignalsLocation'))==bool(old['SignalsLocation'])
 report['refresh_rate_restored']=int(mp.Get('org.freedesktop.ModemManager1.Modem.Location','GpsRefreshRate'))==int(old['GpsRefreshRate'])
 report['elapsed_seconds']=time.monotonic()-started
 watch_after=json.loads((root/'gnss-assist/watch-state.json').read_text());(out/'watch-after-private.json').write_text(json.dumps(watch_after,indent=2)+'\n')
 report['automatic_worker_starts']=watch_after['worker_starts'];report['automatic_worker_completions']=watch_after['worker_completions'];report['automatic_worker_result']=watch_after['last_result']
 afterlog=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(afterlog)
 report['fault_delta']={k:afterlog.count(v)-beforelog.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()}
 (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');bus.close()
print(json.dumps(report))
