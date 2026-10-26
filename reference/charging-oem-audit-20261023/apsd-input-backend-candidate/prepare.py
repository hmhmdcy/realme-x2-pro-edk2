"""Create the opt-in R7 transport candidate locally; never execute it."""
from pathlib import Path
import difflib,hashlib,json
HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
BASE=REF/'charging-session-20261023/r8-source-integration/kernel-sources/drivers/power/supply'
API=REF/'charging-session-20261023/apsd-session-owner-candidate/samurai-apsd-backend.h'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
assert sha(API.read_bytes())=='00d5659e8028a18be6f9db990cb9221af8475cf434693e3b995612f04f6cee94'
source=(BASE/'samurai-usb-input.c').read_text()
assert sha((BASE/'samurai-usb-input.c').read_bytes())=='b712764fbd4ab24475ae1ba030ee4c26c7eb048a6038488a5435b44ef7eb7098'
original=source
def replace(old,new):
 global source
 assert source.count(old)==1,(old,source.count(old))
 source=source.replace(old,new)
replace('/* RMX1931 input observer: no PMIC, charger, USB role or PD writes. */',
        '/* R7 budget observer plus explicit, default-off APSD transport.\n * No charger, USB role, PD or current-policy writes.\n */')
replace('#include "samurai-usb-input-decode.h"',
        '#include "samurai-usb-input-decode.h"\n#include "samurai-apsd-backend.h"\n\nstatic bool apsd_backend;\nmodule_param(apsd_backend, bool, 0444);\nMODULE_PARM_DESC(apsd_backend, "Register the optional owner-controlled APSD transport");')
replace('\tstruct regmap *map;','\tstruct regmap *map;\n\tstruct device *dev;\n\tu64 apsd_sample_serial, apsd_attempt_epoch;\n\tbool apsd_registered, apsd_joining;')
replace('static int samurai_usb_get_budget(', '#include "samurai-apsd-input.inc"\n\nstatic int samurai_usb_get_budget(')
replace('static void samurai_usb_stop(void *data)\n{\n\tstruct samurai_usb_input *input = data;\n\n',
        'static void samurai_usb_stop(void *data)\n{\n\tstruct samurai_usb_input *input = data;\n\n\tsamurai_usb_apsd_withdraw(input);\n')
replace('\tmod_delayed_work(system_wq, &input->work, 0);',
        '\tsamurai_usb_apsd_start(input);\n\tmod_delayed_work(system_wq, &input->work, 0);')
replace('\tinput->map = dev_get_regmap(dev->parent, NULL);','\tinput->dev = dev;\n\tinput->map = dev_get_regmap(dev->parent, NULL);')
replace('\tschedule_delayed_work(&input->work, 0);','\tsamurai_usb_apsd_start(input);\n\tschedule_delayed_work(&input->work, 0);')
outputs={'samurai-usb-input.c':source.encode(),
 'samurai-usb-input-decode.h':(BASE/'samurai-usb-input-decode.h').read_bytes(),
 'samurai-apsd-backend.h':API.read_bytes(),
 'input-backend.patch':''.join(difflib.unified_diff(original.splitlines(True),source.splitlines(True),
   fromfile='a/drivers/power/supply/samurai-usb-input.c',tofile='b/drivers/power/supply/samurai-usb-input.c')).encode()}
for name,raw in outputs.items():
 p=HERE/name
 if p.exists():assert p.read_bytes()==raw,name
 else:
  with p.open('xb') as f:f.write(raw)
print(json.dumps({'generated_local_only':True,'files':{k:sha(v) for k,v in outputs.items()},'device_accessed':False}))
