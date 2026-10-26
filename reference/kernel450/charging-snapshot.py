"""Read and preserve the actual host-authorized USB budget after port changes."""
from pathlib import Path
import hashlib,json,re,runpy
lib=runpy.run_path('/usr/sbin/samurai-charging');meta=lib['verify']()
for name,row in meta['modules'].items():lib['loaded_matches'](Path(row['target']),name.replace('-','_'))
assert hashlib.sha256(Path('/usr/share/samurai-charging/manifest.json').read_bytes()).hexdigest()=='78332c70ee1613f728009e97beaa82e0133299b8225e56069b403f9f1fcf5abe'
ps=Path('/sys/class/power_supply');charger=ps/'mp2650-input';source=ps/'samurai-usb-input'
names=['samurai_usb_input','samurai_gauge_protection','samurai_mp2650']
notes={n:hashlib.sha256(Path('/sys/module',n,'notes/.note.gnu.build-id').read_bytes()).hexdigest() for n in names}
limits={n:int((charger/n).read_text()) for n in ['input_current_limit','constant_charge_current','constant_charge_voltage']}
budget=int((source/'current_max').read_text());native=int((source/'input_current_limit').read_text())
kind=re.search(r'\[([^]]+)\]',(source/'usb_type').read_text());assert kind and kind[1] in ['SDP','CDP']
assert int((source/'online').read_text())==1 and budget in [100000,500000,1500000] and native in [100000,500000]
if kind[1]=='SDP':assert budget==native<=500000
else:assert budget==1500000
assert limits['input_current_limit']==min(900000,budget) and limits['constant_charge_current']==250000 and limits['constant_charge_voltage']<=8725000
udcs=list(Path('/sys/class/udc').iterdir());assert len(udcs)==1 and (udcs[0]/'state').read_text().strip()=='configured'
gadgets=[p for p in Path('/sys/kernel/config/usb_gadget').iterdir() if (p/'UDC').read_text().strip()]
assert len(gadgets)==1
declarations={p.parent.name:int(p.read_text()) for p in (gadgets[0]/'configs').glob('*/MaxPower')};assert len(declarations)==1
declared=next(iter(declarations.values()));assert declared in [100,500] and native<=declared*1000
assert Path('/etc/runlevels/default/samurai-charging').is_symlink()
assert Path('/sys/module/samurai_usb_input/parameters/native_retained').read_text().strip()=='Y'
assert Path('/sys/module/samurai_mp2650/parameters/control').read_text().strip()=='Y'
assert Path('/sys/bus/i2c/devices/0-005c/driver').resolve().name=='samurai-mp2650'
assert Path('/sys/firmware/devicetree/base/soc@0/usb@a6f8800/usb@a600000/usb-psy-name').read_bytes()==b'samurai-usb-input\0'
print(json.dumps(dict(notes=notes,limits=limits,service_enabled=True,native_retained=True,source_type=kind[1],source_budget_ua=budget,native_udc_allowance_ua=native,gadget_maxpower_ma=declared,cpu_capacity={str(i):int(Path('/sys/devices/system/cpu/cpu%d/cpu_capacity'%i).read_text()) for i in range(8)},passed=True)))
