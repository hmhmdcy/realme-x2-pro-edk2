"""Prepare the proven restart sequence for the reviewed one-property DT."""
from pathlib import Path
import hashlib
import json

ref=Path(__file__).resolve().parent
private=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/usb-transition')
private.mkdir(mode=0o700,exist_ok=True)
assert json.loads((ref/'service-test-result.json').read_text())['passed']
build=json.loads((ref/'usb-boot-result.json').read_text())
root=private.parent.parent
paths={'candidate':root/'charging-management-20261023/usb-boot/boot-charging-usb-dt.img',
       'rollback':root/'kernel389/boot-partition-k389-icp-platform.img'}
for name,p in paths.items():
    digest=build['boot_sha256'] if name=='candidate' else build['rollback_boot_sha256']
    assert p.stat().st_size==100663296 and hashlib.sha256(p.read_bytes()).hexdigest()==digest
(private/'transition-lock.json').write_text(json.dumps({'files':{n:str(p) for n,p in paths.items()},'build':build},indent=2))
for name,target in [('recovery-quiesce.py','usb-quiesce.py'),('recovery-restart.py','usb-restart.py')]:
    text=(ref/name).read_text().replace('charging-20261023-recovery','charging-20261023-usb-transition')
    text=text.replace('charging-20261023-reboot-phase-private','charging-20261023-usb-reboot-phase-private')
    text=text.replace("Path('/proc/sys/kernel/tainted').read_text().strip()=='512'","Path('/proc/sys/kernel/tainted').read_text().strip()=='0'")
    text=text.replace("proof['taint']==512","proof['taint']==0").replace('taint=512,','taint=0,')
    text=text.replace('stage=367',"work='charging-usb-dt'")
    if name=='recovery-quiesce.py':
        old="bus=dbus.SystemBus(private=True);objects=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();v=next(x for x in objects.values() if 'org.freedesktop.ModemManager1.Modem' in x)\n assert int(v['org.freedesktop.ModemManager1.Modem.Location']['Enabled'])==0;bus.close();assert not json.loads((r/'gnss-assist/watch-state.json').read_text())['active']"
        new="""assert not json.loads((r/'gnss-assist/watch-state.json').read_text())['active']
 if subprocess.run(['pgrep','-x','ModemManager'],capture_output=True).returncode==0:
  bus=dbus.SystemBus(private=True)
  objects=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
  assert all(int(v['org.freedesktop.ModemManager1.Modem.Location']['Enabled'])==0 for v in objects.values() if 'org.freedesktop.ModemManager1.Modem.Location' in v)
  bus.close()"""
        assert text.count(old)==1;text=text.replace(old,new)
        text=text.replace("['samurai-gnss-assist','bluetooth'","['samurai-charging','samurai-gnss-assist','bluetooth'")
    compile(text,target,'exec');(ref/target).write_text(text)
print(json.dumps({'transition_prepared':True,'candidate_sha256':build['boot_sha256'],'rollback_sha256':build['rollback_boot_sha256'],'executed':False}))
