"""Finite real BLE test against this workstation's dedicated static service."""
from pathlib import Path
import dbus
import hashlib
import json
import os
import re
import subprocess
import time
import traceback

SERVICE = 'f83b8821-f878-46e2-9f51-47da7b509601'
CHARACTERISTIC = 'f83b8821-f878-46e2-9f51-47da7b509602'
EXPECTED = b'samurai-bt-gatt-v1'
out = Path('/var/lib/samurai/bluetooth-20261023-gatt-r1')
out.mkdir(mode=0o700)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
keys = lambda: {str(p):sha(p) for p in Path('/var/lib/bluetooth').glob('**/info')}
before_keys = keys()
bus = dbus.SystemBus(private=True)
assert bus.name_has_owner('org.bluez'), 'Do not activate absent BlueZ service implicitly'
manager = dbus.Interface(bus.get_object('org.bluez', '/'), 'org.freedesktop.DBus.ObjectManager')
objects = manager.GetManagedObjects()
adapters = [(p,v['org.bluez.Adapter1']) for p,v in objects.items() if 'org.bluez.Adapter1' in v]
assert len(adapters) == 1
assert not any(v.get('org.bluez.Device1', {}).get('Connected', False) for v in objects.values())
adapter, saved = adapters[0]
assert not saved['Discovering']
initial_paths = set(str(p) for p in objects)
props = dbus.Interface(bus.get_object('org.bluez', adapter), 'org.freedesktop.DBus.Properties')
control = dbus.Interface(bus.get_object('org.bluez', adapter), 'org.bluez.Adapter1')
state_names = ['Powered','Pairable','Discoverable']
initial = {n: bool(saved[n]) for n in state_names}
report = dict(initial=initial, no_pairing_or_trust_operations=True, reads=[], cleanup_errors=[])
target = None
started = False
monitor = None
log = (out/'btmon-private.log').open('xb')
kernel_before = subprocess.check_output(['dmesg'])
(out/'dmesg-before-private.log').write_bytes(kernel_before)
try:
    monitor = subprocess.Popen(['btmon','-i','hci0','-w',str(out/'hci-private.btsnoop')], stdout=log, stderr=subprocess.STDOUT)
    time.sleep(.2)
    assert monitor.poll() is None
    if not initial['Powered']: props.Set('org.bluez.Adapter1','Powered',dbus.Boolean(True))
    # Properties that require power are set only after power-on succeeds.
    for n in ['Pairable','Discoverable']:
        if bool(props.Get('org.bluez.Adapter1',n)): props.Set('org.bluez.Adapter1',n,dbus.Boolean(False))
    control.SetDiscoveryFilter(dbus.Dictionary({'Transport':dbus.String('le'),
        'UUIDs':dbus.Array([SERVICE],signature='s'),'DuplicateData':dbus.Boolean(False),
        'AutoConnect':dbus.Boolean(False)},signature='sv'))
    control.StartDiscovery(); started = True
    deadline = time.monotonic()+20
    while time.monotonic()<deadline:
        matches = [p for p,v in manager.GetManagedObjects().items()
                   if SERVICE in [str(u).lower() for u in v.get('org.bluez.Device1',{}).get('UUIDs',[])]]
        if len(matches)>1: raise RuntimeError('More than one dedicated test peer')
        if matches: target = matches[0];break
        time.sleep(.2)
    control.StopDiscovery();started=False
    assert target is not None, 'Dedicated Windows GATT peer was not discovered'
    report['peer_path_private'] = str(target)
    device = dbus.Interface(bus.get_object('org.bluez',target),'org.bluez.Device1')
    for cycle in range(2):
        device.Connect(timeout=30)
        deadline=time.monotonic()+20
        characteristic=None
        while time.monotonic()<deadline:
            objs=manager.GetManagedObjects()
            state=objs.get(target,{}).get('org.bluez.Device1',{})
            if state.get('ServicesResolved'):
                chars=[p for p,v in objs.items() if str(p).startswith(str(target)+'/')
                       and str(v.get('org.bluez.GattCharacteristic1',{}).get('UUID','')).lower()==CHARACTERISTIC]
                if len(chars)==1:characteristic=chars[0];break
            time.sleep(.2)
        assert characteristic is not None,'Dedicated characteristic not resolved'
        api=dbus.Interface(bus.get_object('org.bluez',characteristic),'org.bluez.GattCharacteristic1')
        data=bytes(api.ReadValue(dbus.Dictionary({},signature='sv'),timeout=15))
        assert data==EXPECTED, 'ATT payload mismatch'
        report['reads'].append(dict(cycle=cycle+1,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
            connected=bool(state.get('Connected')),services_resolved=bool(state.get('ServicesResolved'))))
        device.Disconnect(timeout=15)
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            if not manager.GetManagedObjects().get(target,{}).get('org.bluez.Device1',{}).get('Connected'):break
            time.sleep(.1)
        assert not manager.GetManagedObjects().get(target,{}).get('org.bluez.Device1',{}).get('Connected')
    report['passed']=True
except Exception:
    report['passed']=False
    report['failure']=traceback.format_exc()
finally:
    def clean(label, function):
        try:function()
        except Exception:report['cleanup_errors'].append(dict(step=label,error=traceback.format_exc()))
    if started:clean('stop-discovery',control.StopDiscovery)
    if target is not None:
        current=manager.GetManagedObjects().get(target,{}).get('org.bluez.Device1',{})
        if current.get('Connected'):clean('disconnect',lambda:dbus.Interface(bus.get_object('org.bluez',target),'org.bluez.Device1').Disconnect(timeout=15))
        if str(target) not in initial_paths and not current.get('Paired'):
            clean('remove-only-new-unpaired-test-peer',lambda:control.RemoveDevice(target))
    clean('release-filter',lambda:control.SetDiscoveryFilter(dbus.Dictionary({},signature='sv')))
    for n in ['Pairable','Discoverable']:
        if bool(props.Get('org.bluez.Adapter1',n)) != initial[n]:
            clean('restore-'+n,lambda n=n:props.Set('org.bluez.Adapter1',n,dbus.Boolean(initial[n])))
    if not initial['Powered']:clean('restore-powered',lambda:props.Set('org.bluez.Adapter1','Powered',dbus.Boolean(False)))
    report['final']={n:bool(props.Get('org.bluez.Adapter1',n)) for n in state_names}
    report['existing_keys_unchanged']=keys()==before_keys
    report['taint']=Path('/proc/sys/kernel/tainted').read_text().strip()
    if monitor is not None:
        monitor.terminate()
        try:monitor.wait(timeout=5)
        except subprocess.TimeoutExpired:monitor.kill();monitor.wait()
    log.close()
    report['kernel_errors_delta']={}
    kernel_after=subprocess.check_output(['dmesg'])
    (out/'dmesg-after-private.log').write_bytes(kernel_after)
    for pattern in [b'Frame reassembly failed',b'WARNING:',b'Oops:',b'Kernel panic',b'slim[^\n]*error']:
        report['kernel_errors_delta'][pattern.decode()]=len(re.findall(pattern,kernel_after))-len(re.findall(pattern,kernel_before))
    report['restored']=not report['cleanup_errors'] and report['final']==initial and report['existing_keys_unchanged']
    report['passed']=bool(report.get('passed') and report['restored'] and report['taint']=='0' and
                          all(v==0 for v in report['kernel_errors_delta'].values()))
    (out/'result-private.json').write_text(json.dumps(report,indent=2)+'\n')
    bus.close()
    print(json.dumps(report))
raise SystemExit(0 if report['passed'] else 1)
