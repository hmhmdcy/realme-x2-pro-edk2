from pathlib import Path
import configparser,dbus,json,os,subprocess,time,traceback

os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k205-diagnostic-cycles';assert not out.exists();out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k205-baseline/boot-id-private.txt').read_bytes() and Path('/sys/module/hci_uart/parameters/samurai_rx_diag').read_text().strip()=='Y'
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
bus=dbus.SystemBus(private=True);obj=bus.get_object('org.bluez','/org/bluez/hci0');ap=dbus.Interface(obj,'org.freedesktop.DBus.Properties');adapter=dbus.Interface(obj,'org.bluez.Adapter1');manager=dbus.Interface(bus.get_object('org.bluez','/'),'org.freedesktop.DBus.ObjectManager')
def state():
 v=ap.GetAll('org.bluez.Adapter1');assert not any(x.get('org.bluez.Device1',{}).get('Connected',False) for x in manager.GetManagedObjects().values());return v
def keys():
 r={}
 for p in Path('/var/lib/bluetooth').rglob('info'):
  c=configparser.ConfigParser(interpolation=None);c.read(p);r[str(p)]={s:dict(c[s]) for s in c.sections() if 'key' in s.lower()}
 return r
original_keys=keys();assert not state()['Powered'] and not state()['Discovering'];before=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(before)
report=dict(stage=205,initialization_cycles=[],payload_capture_observed=False,only_bounded_initialization_and_scan=True,no_pair_connect_or_haptic_commands=True);started=False;failure=None
try:
 for index in range(1,9):
  for name in ['Pairable','Connectable']:ap.Set('org.bluez.Adapter1',name,dbus.Boolean(False),timeout=10)
  begin=time.monotonic();ap.Set('org.bluez.Adapter1','Powered',dbus.Boolean(True),timeout=20);assert state()['Powered']
  for name in ['Pairable','Connectable','Discoverable']:ap.Set('org.bluez.Adapter1',name,dbus.Boolean(False),timeout=10)
  if index==1:
   adapter.SetDiscoveryFilter(dbus.Dictionary({'Transport':dbus.String('auto'),'Discoverable':dbus.Boolean(False),'AutoConnect':dbus.Boolean(False)},signature='sv'),timeout=10)
   adapter.StartDiscovery(timeout=12);started=True;time.sleep(4);adapter.StopDiscovery(timeout=10);started=False
  time.sleep(.4);ap.Set('org.bluez.Adapter1','Powered',dbus.Boolean(False),timeout=15);assert not state()['Powered'] and not state()['Discovering'];time.sleep(.5)
  log=subprocess.check_output(['dmesg']);(out/('dmesg-cycle-'+str(index)+'-private.txt')).write_bytes(log)
  errors=log.count(b'Frame reassembly failed')-before.count(b'Frame reassembly failed');captured=log.count(b'RXDIAG head=')-before.count(b'RXDIAG head=')
  report['initialization_cycles'].append(dict(cycle=index,power_on_off_completed=True,elapsed_seconds=time.monotonic()-begin,reassembly_delta_total=errors,baud_error_chunks_captured=captured))
  report['payload_capture_observed']=captured>0;(out/'progress.json').write_text(json.dumps(report,indent=2)+'\n')
  if captured:break
except Exception:
 failure=traceback.format_exc();(out/'failure-private.txt').write_text(failure)
finally:
 try:
  if state()['Discovering']:adapter.StopDiscovery(timeout=10)
  if state()['Powered']:ap.Set('org.bluez.Adapter1','Powered',dbus.Boolean(False),timeout=15)
  report['bluetooth_restored_off']=not state()['Powered'] and not state()['Discovering'];report['pairing_keys_unchanged']=keys()==original_keys
 except Exception:(out/'cleanup-error-private.txt').write_text(traceback.format_exc());report['cleanup_error']=True
 bus.close();after=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(after);report['fault_delta']={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',reassembly=b'Frame reassembly failed').items()};report['failed']=failure is not None;report['taint']=int(Path('/proc/sys/kernel/tainted').read_text());(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
