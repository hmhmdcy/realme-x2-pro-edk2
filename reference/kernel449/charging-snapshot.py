from pathlib import Path
import hashlib,json,runpy
lib=runpy.run_path('/usr/sbin/samurai-charging');meta=lib['verify']()
for name,row in meta['modules'].items():lib['loaded_matches'](Path(row['target']),name.replace('-','_'))
assert hashlib.sha256(Path('/usr/share/samurai-charging/manifest.json').read_bytes()).hexdigest()=='34d46f4cf449f0c7a50590e0de3c07d84762c19ef1dd1a22e20f6cf66a24d5a7'
"""Read the new persistent charging baseline; never alter it from camera tests."""
from pathlib import Path
import hashlib,json
ps=Path('/sys/class/power_supply');charger=ps/'mp2650-input';source=ps/'samurai-usb-input'
names=['samurai_usb_input','samurai_gauge_protection','samurai_mp2650']
notes={n:hashlib.sha256(Path('/sys/module',n,'notes/.note.gnu.build-id').read_bytes()).hexdigest() for n in names}
static={n:int((charger/n).read_text()) for n in ['input_current_limit','constant_charge_current','constant_charge_voltage']}
assert static['input_current_limit']==900000 and static['constant_charge_current']==250000 and static['constant_charge_voltage']<=8725000
assert Path('/etc/runlevels/default/samurai-charging').is_symlink()
assert Path('/sys/module/samurai_usb_input/parameters/native_retained').read_text().strip()=='Y'
assert Path('/sys/module/samurai_mp2650/parameters/control').read_text().strip()=='Y'
assert Path('/sys/bus/i2c/devices/0-005c/driver').resolve().name=='samurai-mp2650'
assert Path('/sys/firmware/devicetree/base/soc@0/usb@a6f8800/usb@a600000/usb-psy-name').read_bytes()==b'samurai-usb-input\0'
print(json.dumps(dict(notes=notes,limits=static,service_enabled=True,native_retained=True,source_budget_ua=int((source/'current_max').read_text()),native_udc_allowance_ua=int((source/'input_current_limit').read_text()),cpu_capacity={str(i):int(Path('/sys/devices/system/cpu/cpu%d/cpu_capacity'%i).read_text()) for i in range(8)},passed=True)))

