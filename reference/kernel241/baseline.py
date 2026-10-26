"""Read current phone state over the existing strict-key USB transport."""
from pathlib import Path
import importlib.util,json,subprocess

R=Path(__file__).resolve().parent
P=Path('/mnt/e/edk2-samurai-out/kernel241')
P.mkdir(mode=0o700,exist_ok=True)
spec=importlib.util.spec_from_file_location('host241',R.parent/'kernel240/host.py')
host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
code=r'''
from pathlib import Path
import dbus,json,subprocess
r=Path('/var/lib/samurai')
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
bus=dbus.SystemBus(private=True)
objects=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
modems=[(str(p),v) for p,v in objects.items() if 'org.freedesktop.ModemManager1.Modem' in v]
assert len(modems)==1
p,interfaces=modems[0];loc=interfaces['org.freedesktop.ModemManager1.Modem.Location'];modem=interfaces['org.freedesktop.ModemManager1.Modem']
watch=json.loads((r/'gnss-assist/watch-state.json').read_text())
report=dict(stage=241,current236_boot=boot==(r/'k236-runtime/boot-id-private.txt').read_bytes(),
 taint=int(Path('/proc/sys/kernel/tainted').read_text()),location_enabled=int(loc['Enabled']),
 location_signals=bool(loc['SignalsLocation']),gps_refresh=int(loc['GpsRefreshRate']),
 modem_state=int(modem['State']),modem_power=int(modem['PowerState']),
 geoclue_running=bool(bus.name_has_owner('org.freedesktop.GeoClue2')),
 assist_active=bool(watch['active']),assist_running=bool(watch['running']),
 remoteprocs=[dict(name=(x/'name').read_text().strip(),state=(x/'state').read_text().strip()) for x in Path('/sys/class/remoteproc').glob('remoteproc*')],
 readonly=True)
bus.close();print(json.dumps(report))
'''
try:
    result=host.ssh('python3 -',input=code.encode(),timeout=20)
except Exception:
    (P/'baseline-failed.txt').write_text('Strict-key transport or read-only state query failed; no mutation dispatched.\n')
    raise
(P/'baseline-host-private.log').write_bytes(result.stdout+result.stderr)
report=json.loads(result.stdout)
(R/'baseline-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
