from pathlib import Path
import dbus,hashlib,json,os,runpy,subprocess,time
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k201-real-expired-flow';assert not out.exists();out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k201-baseline/boot-id-private.txt').read_bytes()
assert hashlib.sha256(Path('/usr/sbin/samurai-gnss-assist').read_bytes()).hexdigest()=='cf3d92a46e619ceba30342fb2c063fb39ba9de5ddd2043e5dc0a5f59f39bef41'
ns=runpy.run_path('/usr/sbin/samurai-gnss-assist',run_name='expired_flow_validation')
bus=dbus.SystemBus(private=True);obj=bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0');props=dbus.Interface(obj,'org.freedesktop.DBus.Properties');api=dbus.Interface(obj,'org.freedesktop.ModemManager1.Modem.Location')
assert int(props.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'))==0 and not bus.name_has_owner('org.freedesktop.GeoClue2')
fresh=(root/'k201-assistance/xtra-private.bin').read_bytes();old=(root/'k191-assistance/xtra-private.bin').read_bytes()
assert hashlib.sha256(fresh).hexdigest()=='303702930b278083fa4e52eeeb99787f511b4b2e150a4dba5161e46f06f335f4'
assert hashlib.sha256(old).hexdigest()=='e905a7291990c20324210b3bb405d84f8088da283f969255e2b28e34676d4008'
before=ns['loc_exchange']('validity');assert ns['validity_current'](before['start'],before['hours'],time.time())
(out/'last-known-good-private.bin').write_bytes(fresh);(out/'before.json').write_text(json.dumps(before,indent=2)+'\n')
for action in ['stop','start']:
 p=subprocess.run(['rc-service','samurai-gnss-assist',action],capture_output=True,text=True,timeout=20);(out/(action+'-private.txt')).write_text(p.stdout+p.stderr);assert p.returncode==0
time.sleep(3);state=root/'gnss-assist/watch-state.json';assert json.loads(state.read_text())['worker_starts']==0
report=dict(stage=201,controlled_expired_runtime_assistance_test=True,modem_reset_requested=False,power_state_changed=False,old_injection_requests=0,old_injection_ack=False,stale_window_established=False,standard_desktop_application_run=False,fallback_fresh_injection_requests=0)
def save():(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
save()
try:
 report['old_injection_requests']=1;save()
 try:
  api.InjectAssistanceData(dbus.ByteArray(old),timeout=120);report['old_injection_ack']=True
 except dbus.DBusException as error:report['old_injection_error_name']=error.get_dbus_name()
 time.sleep(1);stale=ns['loc_exchange']('validity');report['after_old_injection']=stale
 report['stale_window_established']=not ns['validity_current'](stale['start'],stale['hours'],time.time());save()
 if report['stale_window_established']:
  with (out/'desktop-test-output-private.json').open('wb') as stdout,(out/'desktop-test-error-private.txt').open('wb') as stderr:
   child=subprocess.run(['/usr/bin/python3',str(root/'k201-expired-flow-tools/test-geoclue-expired-auto.py')],stdout=stdout,stderr=stderr)
  report['desktop_test_exit']=child.returncode;report['standard_desktop_application_run']=True
  desktop=root/'k201-geoclue-expired-auto/summary.json'
  if desktop.exists():report['desktop']=json.loads(desktop.read_text())
  # Let the service's own bounded request finish before any independent recovery.
  while True:
   watch=json.loads(state.read_text())
   if watch['worker_starts']==watch['worker_completions']:break
   time.sleep(2)
  report['automatic_worker']=watch;save()
finally:
 assert int(props.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'))==0
 after=ns['loc_exchange']('validity')
 if not ns['validity_current'](after['start'],after['hours'],time.time()):
  report['fallback_fresh_injection_requests']=1;save();api.InjectAssistanceData(dbus.ByteArray(fresh),timeout=120);time.sleep(1);after=ns['loc_exchange']('validity')
 report['final_validity']=after;report['final_file_current']=ns['validity_current'](after['start'],after['hours'],time.time());report['gps_enabled_final']=int(props.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'));save();bus.close()
 assert report['final_file_current'] and report['gps_enabled_final']==0
print(json.dumps(report))
