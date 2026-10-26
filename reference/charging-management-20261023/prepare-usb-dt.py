"""Add one native DWC3 supply-name property to the exact current boot DT."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys

ref=Path(__file__).resolve().parent
sys.path.insert(0,str(ref.parent/'kernel284'));import storage
shared=storage.mounted_build();source=shared.parent/'source354'
private=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/usb-dt')
private.mkdir(mode=0o700,exist_ok=True)
baseline=private.parent.parent/'kernel389/samurai389-private.dtb'
receipt=json.loads((ref.parent/'kernel389/build-package-validation.json').read_text())
assert hashlib.sha256(baseline.read_bytes()).hexdigest()==receipt['dtb_sha256']
assert json.loads((ref/'boot-baseline-result.json').read_text())['boot_sha256']==receipt['boot_sha256']
ns={};exec((ref.parent/'kernel93/verify-firmware.py').read_text().split('\ndt_audit=')[0],ns)
parse=ns['fdt_nodes'];before=parse(baseline.read_bytes())
live=parse((private.parent/'boot-baseline/live-private.dtb').read_bytes())
paths=[p for p,d in before.items() if b'snps,dwc3' in d.get('compatible',b'').split(b'\0') and p.endswith('/usb@a600000')]
assert len(paths)==1;path=paths[0]
assert before[path]==live[path] and 'usb-psy-name' not in before[path]
candidate=private/'samurai-charging-usb-private.dtb';shutil.copyfile(baseline,candidate)
subprocess.run(['fdtput','-t','s',str(candidate),path,'usb-psy-name','samurai-usb-input'],check=True)
after=parse(candidate.read_bytes())
assert before.keys()==after.keys()
delta=[(p,k) for p in before for k in before[p].keys()|after[p].keys() if before[p].get(k)!=after[p].get(k)]
assert delta==[(path,'usb-psy-name')] and after[path]['usb-psy-name']==b'samurai-usb-input\0'
core=(source/'drivers/usb/dwc3/core.c').read_text();gadget=(source/'drivers/usb/dwc3/gadget.c').read_text()
assert 'usb-psy-name' in core and 'POWER_SUPPLY_PROP_INPUT_CURRENT_LIMIT' in core
for name,text,needle,lines in [('core',core,'dwc3_get_usb_power_supply(',95),
                               ('gadget',gadget,'dwc3_gadget_vbus_draw(',45)]:
    start=text.index(needle)
    (private/(name+'-native-budget-source.txt')).write_text('\n'.join(text[start:].splitlines()[:lines])+'\n')
    print((private/(name+'-native-budget-source.txt')).read_text())
config=(shared/'.config').read_text()
report={'passed':True,'base_boot_stage':390,'base_dt_stage':389,'dwc3_node':path,
    'semantic_changes':[{'node':p,'property':k} for p,k in delta],
    'all_other_properties_byte_exact':True,'existing_phandles_unchanged':True,
    'dtb_sha256':hashlib.sha256(candidate.read_bytes()).hexdigest(),
    'rollback_boot_sha256':receipt['boot_sha256'],'candidate_deployed':False,
    'native_source_sha256':{n:hashlib.sha256((source/'drivers/usb/dwc3'/n).read_bytes()).hexdigest() for n in ['core.c','gadget.c']},
    'pm_test_available':'CONFIG_PM_DEBUG=y' in config,'runtime_providers_required':True}
(ref/'usb-dt-result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
