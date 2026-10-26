"""One-shot real BlueZ D-Bus discovery, MGMT/HCI capture, and bounded cleanup."""
import hashlib, json, os, shutil, signal, struct, subprocess, sys, threading, time, traceback
from pathlib import Path
import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib
sys.path.insert(0,'/var/lib/samurai/k185-tools')
from bt_mgmt import Management, open_channel, snapshot

os.umask(0o077)
root=Path(sys.argv[1])
root.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k185-baseline/boot-id-private.txt').read_bytes()
assert subprocess.check_output(['uname','-v'],text=True).startswith('#183 ')
assert subprocess.run(['pgrep','-x','bluetoothd'],stdout=subprocess.DEVNULL).returncode==0
(root/'boot-id-private.txt').write_bytes(Path('/proc/sys/kernel/random/boot_id').read_bytes())
def save(name,value): (root/name).write_text(json.dumps(value,indent=2,default=str)+'\n')
def capture(name,command):
    with (root/name).open('xb') as f: subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=15)
capture('dmesg-before.txt',['dmesg'])
initial_gui={name:subprocess.check_output(['pgrep','-x',name],text=True).strip() for name in ('phosh','phoc')}
probe=Management(root/'probe-mgmt-private.jsonl',allow_scan=True)
initial=snapshot(probe); save('mgmt-initial-private.json',initial)
assert initial['configured']==[0] and not initial['unconfigured']
assert initial['info']['settings'] & (1|2|8|16)==0
query=Path('/run/samurai-radio-address/current-bt').read_text().strip()
address=Path(query,'bt-mac-le.bin').read_bytes()
assert initial['info']['address_le']==address.hex()
shutil.copytree('/var/lib/bluetooth', root/'bluetooth-storage-before-private', symlinks=True)
DBusGMainLoop(set_as_default=True)
bus=dbus.SystemBus(private=True)
assert bus.name_has_owner('org.bluez')
stop=threading.Event(); monitor=open_channel(2); monitor.settimeout(0.5)
events=Management(root/'events-mgmt-private.jsonl')
errors=[]
def record_hci():
    with (root/'hci-monitor-private.jsonl').open('x') as f:
        while not stop.is_set():
            try: b=monitor.recv(65535)
            except TimeoutError: continue
            except OSError as e:
                if stop.is_set(): break
                errors.append(str(e)); break
            f.write(json.dumps(dict(monotonic=time.monotonic(),packet=b.hex()))+'\n'); f.flush()
def record_mgmt():
    while not stop.is_set():
        try: events.receive(0.5)
        except Exception as e: errors.append(str(e)); break
threads=[threading.Thread(target=f,daemon=True) for f in (record_hci,record_mgmt)]
for t in threads: t.start()
config=root/'bluez-test-private.conf'
config.write_text('[General]\nAlwaysPairable=false\n[Policy]\nAutoEnable=false\n')
daemon=None; props=None; adapter=None; active=False; rounds=[]; failure=None
signals=[]; health=[]; context=GLib.MainContext.default()
log=(root/'bluetoothd-private.txt').open('xb')
def changed(*args,**kwargs): signals.append(dict(monotonic=time.monotonic(),args=args,meta=kwargs))
bus.add_signal_receiver(changed,signal_name='InterfacesAdded',dbus_interface='org.freedesktop.DBus.ObjectManager',bus_name='org.bluez',path_keyword='object_path')
bus.add_signal_receiver(changed,signal_name='PropertiesChanged',dbus_interface='org.freedesktop.DBus.Properties',bus_name='org.bluez',path_keyword='object_path')
def pump(seconds):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        while context.pending(): context.iteration(False)
        time.sleep(0.05)
def properties(): return dict(props.GetAll('org.bluez.Adapter1',timeout=8))
def wait_property(name,value,bound=10):
    end=time.monotonic()+bound
    while time.monotonic()<end:
        p=properties()
        if bool(p[name])==value: return p
        pump(0.2)
    raise TimeoutError('Adapter property '+name)
def sample():
    assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
    for name,pid in initial_gui.items(): assert subprocess.check_output(['pgrep','-x',name],text=True).strip()==pid
    link=subprocess.check_output(['iw','dev','wlan0','link'],text=True)
    assert 'freq: 5180' in link
    assert Path('/sys/class/remoteproc/remoteproc1/state').read_text().strip()=='running'
    assert Path('/sys/class/remoteproc/remoteproc2/state').read_text().strip()=='running'
    health.append(dict(monotonic=time.monotonic(),frequency_mhz=5180,taint=0,gui_same=True,radio_audio_running=True))
def alarm_handler(sig,frame): raise TimeoutError('discovery overall bound')
signal.signal(signal.SIGALRM,alarm_handler); signal.alarm(150)
try:
    dbus_api=dbus.Interface(bus.get_object('org.freedesktop.DBus','/org/freedesktop/DBus'),'org.freedesktop.DBus')
    owner_pid=int(dbus_api.GetConnectionUnixProcessID('org.bluez',timeout=8))
    assert owner_pid in [int(x) for x in subprocess.check_output(['pgrep','-x','bluetoothd'],text=True).split()]
    service_status=subprocess.check_output(['rc-service','bluetooth','status'],text=True)
    assert 'status: started' in service_status
    (root/'service-status-before.txt').write_text(service_status)
    objman=dbus.Interface(bus.get_object('org.bluez','/'),'org.freedesktop.DBus.ObjectManager')
    end=time.monotonic()+15; objects={}
    while time.monotonic()<end:
        objects=objman.GetManagedObjects(timeout=8)
        if '/org/bluez/hci0' in objects: break
        pump(0.2)
    assert '/org/bluez/hci0' in objects
    save('objects-before-private.json',objects); assert all(not v.get('org.bluez.Device1',{}).get('Connected',False) and not v.get('org.bluez.Device1',{}).get('Paired',False) and not v.get('org.bluez.Device1',{}).get('Bonded',False) for v in objects.values())
    obj=bus.get_object('org.bluez','/org/bluez/hci0')
    props=dbus.Interface(obj,'org.freedesktop.DBus.Properties'); adapter=dbus.Interface(obj,'org.bluez.Adapter1')
    p=properties(); save('adapter-before-private.json',p)
    assert p['Address'].lower()==':'.join(f'{x:02x}' for x in address[::-1])
    assert not p['Powered'] and not p['Discovering']
    for key in ('Pairable','Connectable'): props.Set('org.bluez.Adapter1',key,dbus.Boolean(False),timeout=8)
    props.Set('org.bluez.Adapter1','Powered',dbus.Boolean(True),timeout=12)
    p=wait_property('Powered',True)
    for key in ('Pairable','Connectable','Discoverable'):
        if p[key]: props.Set('org.bluez.Adapter1',key,dbus.Boolean(False),timeout=8)
    p=properties(); assert all(not p[k] for k in ('Pairable','Connectable','Discoverable'))
    save('adapter-powered-private.json',p); sample()
    for transport,seconds in [('le',12),('bredr',12),('auto',20)]:
        adapter.SetDiscoveryFilter(dbus.Dictionary({'Transport':dbus.String(transport),'Discoverable':dbus.Boolean(False),'AutoConnect':dbus.Boolean(False),'DuplicateData':dbus.Boolean(False)},signature='sv'),timeout=8)
        first_signal=len(signals); before=time.monotonic()
        adapter.StartDiscovery(timeout=12); active=True
        p=wait_property('Discovering',True)
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            sample(); pump(min(2,end-time.monotonic()))
        adapter.StopDiscovery(timeout=12); active=False
        p=wait_property('Discovering',False)
        current=objman.GetManagedObjects(timeout=8)
        save(f'objects-{transport}-private.json',current)
        devices={str(path):value['org.bluez.Device1'] for path,value in current.items() if 'org.bluez.Device1' in value}
        assert all(not d.get('Connected',False) and not d.get('Paired',False) and not d.get('Bonded',False) for d in devices.values())
        assert all(not p[k] for k in ('Pairable','Connectable','Discoverable'))
        rounds.append(dict(transport=transport,requested_seconds=seconds,duration_seconds=time.monotonic()-before,devices=len(devices),new_signal_count=len(signals)-first_signal,discovery_started=True,discovery_stopped=True,paired_connected_bonded=False))
        pump(1)
except Exception as e:
    failure=str(e); (root/'failure-private.txt').write_text(traceback.format_exc())
finally:
    signal.alarm(0)
    cleanup=[]
    if props is not None:
        try:
            if active: adapter.StopDiscovery(timeout=12); active=False
            if properties().get('Powered'): props.Set('org.bluez.Adapter1','Powered',dbus.Boolean(False),timeout=12)
            p=wait_property('Powered',False); assert not p['Discovering']; save('adapter-final-private.json',p)
            cleanup.append('discovery_off_power_off')
        except Exception as e: errors.append('D-Bus cleanup: '+str(e))
    if daemon is not None and daemon.poll() is None:
        daemon.terminate()
        try: daemon.wait(timeout=10)
        except subprocess.TimeoutExpired: errors.append('daemon failed bounded TERM'); daemon.kill(); daemon.wait(timeout=5)
    log.close()
    final=snapshot(probe)
    if final['info']['settings'] & 1:
        probe.command(5,0,b'\0'); final=snapshot(probe); cleanup.append('management_fallback_power_off')
    save('mgmt-final-private.json',final)
    assert final['info']['address_le']==address.hex() and not final['info']['settings'] & 1
    stop.set()
    for t in threads: t.join(timeout=2)
    monitor.close(); events.close(); probe.close(); bus.close()
    save('signals-private.json',signals); save('health.json',health)
    save('result.json',dict(kernel=183,rounds=rounds,original_daemon_stopped=False,daemon_stopped=False,daemon_service_running=True,final_powered=False,verified_dms_address_retained_in_ram=True,
                            cleanup=cleanup,monitor_errors=errors,failure=failure,pass_all=failure is None and not errors and len(rounds)==3))
    capture('service-status-after.txt',['rc-service','bluetooth','status'])
    capture('dmesg-after.txt',['dmesg'])
    print(json.dumps(dict(rounds=len(rounds),failure=failure,monitor_errors=errors,final_powered=False)))
if failure or errors: sys.exit(1)
