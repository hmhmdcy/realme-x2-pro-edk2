from pathlib import Path
import dbus,hashlib,json,os,subprocess,time,traceback

os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k204-bt-scan-pm-r2';assert not out.exists();out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k204-runtime/boot-id-private.txt').read_bytes()
policy=root/'k204-bt-policy-r2';assert policy.is_dir();config=Path('/etc/bluetooth/main.conf');initial_config=(policy/'main.conf-before-private').read_bytes()
bus=dbus.SystemBus(private=True);obj=bus.get_object('org.bluez','/org/bluez/hci0');ap=dbus.Interface(obj,'org.freedesktop.DBus.Properties');adapter=dbus.Interface(obj,'org.bluez.Adapter1');manager=dbus.Interface(bus.get_object('org.bluez','/'),'org.freedesktop.DBus.ObjectManager')
def state():
 p=ap.GetAll('org.bluez.Adapter1');assert all(not v.get('org.bluez.Device1',{}).get('Connected',False) for v in manager.GetManagedObjects().values());return p
def keys():
 import configparser
 result={}
 for p in Path('/var/lib/bluetooth').rglob('info'):
  c=configparser.ConfigParser(interpolation=None);c.read(p);result[str(p)]={s:dict(c[s]) for s in c.sections() if 'key' in s.lower()}
 return result
before_keys=keys();before_log=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(before_log)
assert not state()['Powered'] and not state()['Discovering'];report=dict(stage=204,boot204_wake_candidate=True,only_scan_and_rtc_suspend=True,slpi_offline_from_recorded_failure=True)
failure=None
def scan(label):
 adapter.SetDiscoveryFilter(dbus.Dictionary({'Transport':dbus.String('auto'),'Discoverable':dbus.Boolean(False),'AutoConnect':dbus.Boolean(False),'DuplicateData':dbus.Boolean(False)},signature='sv'),timeout=10)
 active=False
 try:
  adapter.StartDiscovery(timeout=15);active=True;assert state()['Discovering'];time.sleep(8)
  objects=manager.GetManagedObjects();(out/(label+'-objects-private.json')).write_text(json.dumps(dict(objects),default=str))
  report[label+'_devices']=sum('org.bluez.Device1' in v for v in objects.values())
 finally:
  if active:adapter.StopDiscovery(timeout=10)
 assert not state()['Discovering'];report[label+'_scan_stopped']=True
try:
 for name in ['Pairable','Connectable']:ap.Set('org.bluez.Adapter1',name,dbus.Boolean(False),timeout=10)
 ap.Set('org.bluez.Adapter1','Powered',dbus.Boolean(True),timeout=15);assert state()['Powered']
 for name in ['Pairable','Connectable','Discoverable']:ap.Set('org.bluez.Adapter1',name,dbus.Boolean(False),timeout=10)
 scan('before_pm')
 p=subprocess.run(['python3','/var/lib/samurai/k204-bt-tools/test-powered-suspend.py',str(out/'powered-suspend')],capture_output=True,timeout=120);(out/'pm-worker-private.log').write_bytes(p.stdout+p.stderr)
 report['pm_returncode']=p.returncode
 if (out/'powered-suspend/validation.json').exists():report['pm']=json.loads((out/'powered-suspend/validation.json').read_text())
 # A failed PM is preserved; only scan if the same adapter is still responsive.
 assert p.returncode==0
 scan('after_pm')
except Exception:
 failure=traceback.format_exc();(out/'failure-private.txt').write_text(failure)
finally:
 try:
  if state()['Discovering']:adapter.StopDiscovery(timeout=10)
  if state()['Powered']:ap.Set('org.bluez.Adapter1','Powered',dbus.Boolean(False),timeout=15)
  report['final_bluetooth_powered']=bool(state()['Powered']);report['final_discovering']=bool(state()['Discovering'])
  assert not report['final_bluetooth_powered'] and not report['final_discovering']
  bus.close();subprocess.run(['rc-service','bluetooth','stop'],capture_output=True,check=True,timeout=25)
  config.write_bytes(initial_config);subprocess.run(['rc-service','bluetooth','start'],capture_output=True,check=True,timeout=30)
  report['config_restored']=config.read_bytes()==initial_config;report['pairing_keys_unchanged']=keys()==before_keys
 except Exception:
  (out/'cleanup-error-private.txt').write_text(traceback.format_exc());report['cleanup_error']=True
 after=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(after)
 report['fault_delta']={k:after.count(v)-before_log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',bluetooth=b'Frame reassembly failed',slpi_fatal=b'fatal error received').items()}
 report['taint']=int(Path('/proc/sys/kernel/tainted').read_text());report['passed']=failure is None and not report.get('cleanup_error') and not any(report['fault_delta'].values()) and report['taint']==0
 (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
assert report['passed']
