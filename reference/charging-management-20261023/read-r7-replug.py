"""One guarded, read-only source and desktop-state snapshot after the real replug."""
from pathlib import Path
import ast
import importlib.util
import json

REF=Path(__file__).resolve().parent
OUT=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/r7-replug')
OUT.mkdir(mode=0o700,exist_ok=True)
candidate=REF.parent/'charging-oem-audit-20261023/normal-restart-candidate/r7-postboot.py'
source=candidate.read_text();tree=ast.parse(source)
pmic=next(ast.get_source_segment(source,n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='pmic_status')
code='from pathlib import Path\nimport dbus,json,os,re,time\n'+pmic+'\n'+r'''
def read(path):
 try:return Path(path).read_text().strip()
 except OSError as e:return {'errno':e.errno}
start=time.clock_gettime(time.CLOCK_BOOTTIME);ps=Path('/sys/class/power_supply')
source={n:read(ps/'samurai-usb-input'/n) for n in ['online','usb_type','current_max','input_current_limit']}
charger={n:read(ps/'mp2650-input'/n) for n in ['online','health','status','charge_behaviour','input_current_limit','constant_charge_current','constant_charge_voltage']}
sample={k:int(v) for k,v in (x.split('=') for x in Path('/sys/bus/i2c/devices/0-005c/telemetry').read_text().split())}
pmic=pmic_status();protection=read('/sys/devices/platform/samurai-gauge-protection/protection_state')
battery={n:read(ps/'bq28z610-0'/n) for n in ['status','current_now','capacity','temp']}
bus=dbus.SystemBus(private=True)
try:
 prop=dbus.Interface(bus.get_object('org.freedesktop.UPower','/org/freedesktop/UPower/devices/DisplayDevice'),'org.freedesktop.DBus.Properties')
 upower={str(k):v for k,v in prop.GetAll('org.freedesktop.UPower.Device').items() if str(k) in ['State','IsPresent','Percentage','EnergyRate','UpdateTime','IconName']}
 root=dbus.Interface(bus.get_object('org.freedesktop.UPower','/org/freedesktop/UPower'),'org.freedesktop.DBus.Properties')
 upower['OnBattery']=bool(root.Get('org.freedesktop.UPower','OnBattery'))
finally:bus.close()
print(json.dumps({'source':source,'charger':charger,'sample':sample,'pmic':pmic,
 'protection_state':protection,'battery':battery,'upower':upower,
 'taint':read('/proc/sys/kernel/tainted'),'read_start_boottime':start,
 'read_end_boottime':time.clock_gettime(time.CLOCK_BOOTTIME)}))
'''
spec=importlib.util.spec_from_file_location('window',REF/'device-window.py')
window=importlib.util.module_from_spec(spec);spec.loader.exec_module(window)
q=window.host.ssh('python3 -',input=code.encode(),timeout=20,check=False)
(OUT/'fresh-source-stdout-private.json').write_bytes(q.stdout)
(OUT/'fresh-source-stderr-private.txt').write_bytes(q.stderr)
if q.returncode:
    print(q.stderr.decode(errors='replace')[-1800:]);raise SystemExit(q.returncode)
data=json.loads(q.stdout)
print(json.dumps(data,indent=2))
