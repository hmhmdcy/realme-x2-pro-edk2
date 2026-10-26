"""Merge the disabled transport into the actual USB13f IRQ/PM source."""
from pathlib import Path
import difflib,hashlib,json,re
HERE=Path(__file__).resolve().parent;CURRENT=HERE.parent/'usb-input-irq-wake-candidate';BUS=HERE.parent/'apsd-final-transfer-candidate'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
current=(CURRENT/'samurai-usb-input.c').read_bytes();record=json.loads((CURRENT/'ko-result.json').read_bytes())
assert record['passed'] and record['source_sha256']==sha(current)=='1ad0c168874448dabd6a38121a7a6b6b73384856798cbefdefaa4b759da9e2bc'
assert record['module_sha256']=='13f41e7cdbd1825982e2155bfb97e0105227179d1afa8da8a2795ba39f4299a4'
source=current.decode()
def replace(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
source=replace(source,'/* RMX1931 input observer: no PMIC, charger, USB role or PD writes. */',
    '/* Current IRQ/native-PM budget observer; optional APSD transport defaults off.\n * No charger, USB role, PD or current-policy writes.\n */')
source=replace(source,'#include "samurai-usb-input-decode.h"','#include "samurai-usb-input-decode.h"\n#include "samurai-apsd-backend.h"\n\nstatic bool apsd_backend;\nmodule_param(apsd_backend, bool, 0444);\nMODULE_PARM_DESC(apsd_backend, "Register the optional owner-controlled APSD transport");')
source=replace(source,'\tstruct regmap *map;','\tstruct regmap *map;\n\tu64 apsd_sample_serial, apsd_attempt_epoch;\n\tbool apsd_registered, apsd_joining;')
source=replace(source,'static int samurai_usb_get_budget(', '#include "samurai-apsd-input.inc"\n\nstatic int samurai_usb_get_budget(')
source=replace(source,'\tmutex_unlock(&input->lock);\n\tcancel_delayed_work_sync(&input->work);',
    '\tmutex_unlock(&input->lock);\n\tsamurai_usb_apsd_withdraw(input);\n\tcancel_delayed_work_sync(&input->work);')
source=replace(source,'\tinput->pm_prepared = true;\n\tmutex_unlock(&input->lock);\n\treturn 0;',
    '\tinput->pm_prepared = true;\n\tmutex_unlock(&input->lock);\n\tsamurai_usb_apsd_withdraw(input);\n\treturn 0;')
source=replace(source,'\tmutex_unlock(&input->lock);\n}\n\nstatic const struct dev_pm_ops',
    '\tmutex_unlock(&input->lock);\n\tsamurai_usb_apsd_start(input);\n}\n\nstatic const struct dev_pm_ops')
source=replace(source,'\tmutex_unlock(&input->lock);\n\tsamurai_usb_retain_for_native_consumer(dev);',
    '\tmutex_unlock(&input->lock);\n\tsamurai_usb_apsd_start(input);\n\tsamurai_usb_retain_for_native_consumer(dev);')
inc=(BUS/'samurai-apsd-input.inc').read_text().replace('input->dev','input->event_dev')
inc=replace(inc,'if (input->paused || input->apsd_joining)', 'if (input->paused || input->pm_prepared || input->apsd_joining)')
inc=replace(inc,'if (input->apsd_registered) {','if (input->apsd_registered || input->paused || input->pm_prepared) {')
files={'samurai-usb-input.c':source.encode(),'samurai-apsd-input.inc':inc.encode(),
    'samurai-apsd-backend.h':(BUS/'samurai-apsd-backend.h').read_bytes(),
    'samurai-usb-input-decode.h':(CURRENT/'samurai-usb-input-decode.h').read_bytes()}
for name,raw in files.items():
    path=HERE/name
    if path.exists():assert path.read_bytes()==raw,name
    else:path.write_bytes(raw)
patch=''.join(difflib.unified_diff(current.decode().splitlines(True),source.splitlines(True),
    fromfile='a/drivers/power/supply/samurai-usb-input.c',tofile='b/drivers/power/supply/samurai-usb-input.c'))
(HERE/'current-usb.patch').write_text(patch)
result=dict(prepared=True,actual_current_source_sha256=sha(current),actual_current_module_sha256=record['module_sha256'],
    files={name:sha(raw) for name,raw in files.items()},phone_accessed=False,transport_defaults_off=True)
(HERE/'source-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(prepared=True,actual_current_USB13f_source=True,transport_defaults_off=True)))
