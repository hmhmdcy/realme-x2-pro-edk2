"""Derive from the actual charger97c source; preserve existing policy/wire code."""
from pathlib import Path
import difflib,hashlib,json
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'charger-reattach-observation-candidate'
R8=HERE.parent/'r8-source-integration/kernel-sources/drivers/power/supply'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
build=json.loads((HERE.parent/'charger-reattach-observation-module-candidate/ko-result.json').read_bytes())
raw=(BASE/'samurai-mp2650.c').read_bytes()
assert build['passed'] and build['module_sha256']=='97c16c3dc0b458fa4d2c686912ffdf805b899abfb846201767843a0348cbffdd'
assert sha(raw)==build['sources']['samurai-mp2650.c']
source=raw.decode().replace('\r\n','\n');old=source
def replace(a,b):
 global source
 assert source.count(a)==1,a
 source=source.replace(a,b)
replace('#include "charge-cycle.h"','#include "charge-cycle.h"\n#include "charge-cycle-hold.h"')
replace('bool auto_requested, latched, paused, sample_full;',
        'bool auto_requested, latched, paused, sample_full;\n\tbool timer_hold_confirmed;')
replace('c->sample.session_seconds = sm_cycle_update(&c->cycle, now, source, healthy_full);',
'''c->sample.session_seconds = sm_cycle_update_held(&c->cycle, now, source, healthy_full,
		c->timer_hold_confirmed && c->sample.valid && c->sample.protection_ok &&
		!c->sample.fault && !c->latched && !c->stop_error &&
		(!validation || reason == SM_POLICY_REASON_GAUGE_CHARGE_STOP ||
		 sm_policy_reason_is_thermal(reason)));''')
replace('\tif (control) {\n\t\tif (ret || c->latched || !c->auto_requested ||',
        '\tc->timer_hold_confirmed = false;\n\tif (control) {\n\t\tif (ret || c->latched || !c->auto_requested ||')
replace('''			c->stop_error = sm_stop(&c->io);
			if (c->stop_error) c->latched = true;
			if (!ret) ret = c->stop_error;''',
'''			c->stop_error = sm_stop(&c->io);
			if (c->stop_error) c->latched = true;
			c->timer_hold_confirmed = source == 1 && !c->stop_error && !c->latched &&
				(!c->auto_requested || c->gauge_charge_stop || sm_policy_reason_is_thermal(reason));
			if (!ret) ret = c->stop_error;''')
with (HERE/'samurai-mp2650.c').open('x') as f:f.write(source)
patch=''.join(difflib.unified_diff(old.splitlines(True),source.splitlines(True),fromfile='a/samurai-mp2650.c',tofile='b/samurai-mp2650.c'))
header=(HERE/'charge-cycle-hold.h').read_text()
patch+=''.join(difflib.unified_diff([],header.splitlines(True),fromfile='/dev/null',tofile='b/charge-cycle-hold.h'))
(HERE/'timer-hold.patch').write_text(patch)
result=dict(passed=True,baseline_charger_ko_sha256=build['module_sha256'],baseline_C_sha256=sha(raw),candidate_C_sha256=sha(source.encode()),
            unchanged_headers={n:d for n,d in build['sources'].items() if n!='samurai-mp2650.c'},
            only_step_function_changed=True,new_private_state='last successful hardware stop',
            phone_accessed=False,installed=False,existing_timeout_and_full_rules_retained=True)
with (HERE/'source-result.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(dict(prepared=True,installed=False)))
