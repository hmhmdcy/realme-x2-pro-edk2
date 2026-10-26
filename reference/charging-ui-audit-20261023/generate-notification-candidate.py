"""Generate a reviewable candidate/patch in this directory only."""
from pathlib import Path
import difflib
import hashlib
import json

ROOT = Path(__file__).resolve().parent
LIVE = ROOT.parent / 'charging-management-20261023' / 'samurai-mp2650.c'
CANDIDATE = ROOT / 'candidate'
CANDIDATE.mkdir(exist_ok=True)
base_path = ROOT / 'before-notification-samurai-mp2650.c'
if not base_path.exists():
    base_path.write_bytes(LIVE.read_bytes())
base = base_path.read_text()
candidate = base


def replace(old, new):
    global candidate
    assert candidate.count(old) == 1, old
    candidate = candidate.replace(old, new)


replace('#include "gauge-i2c.h"', '#include "gauge-i2c.h"\n#include "charging-notify.h"')
replace('struct power_supply *input, *protection, *psy;',
        'struct power_supply *input, *protection, *psy, *battery;')
replace('\tbool notifier_registered;\n',
        '\tbool notifier_registered;\n\tstruct sm_notify_state notified;\n\tbool notified_valid;\n')
replace('static void sm_poll(struct work_struct *work)', '''/* Called after the safety step, with c->lock held and no I2C bus lock held.
 * bq27xxx STATUS reads its own signed current/FC flags; do not infer net battery
 * charging from CHG_EN or the charger's switching state.
 */
static bool sm_notification_locked(struct sm_charger *c)
{
	struct sm_notify_state state = {
		.health = c->last_error || c->latched || c->stop_error ?
			POWER_SUPPLY_HEALTH_UNSPEC_FAILURE : POWER_SUPPLY_HEALTH_GOOD,
		.error = c->last_error,
		.stop_error = c->stop_error,
		.latched = c->latched,
		.source_inhibit = c->source_inhibit,
		.auto_requested = c->auto_requested,
		.valid = c->sample.valid,
		.online = c->sample.online,
		.protection_ok = c->sample.protection_ok,
		.fault = c->sample.fault,
		.target_enable = c->target.enable,
		.input_ua = c->target.input_ua,
		.current_ua = c->target.current_ua,
		.cell_uv = c->target.cell_uv,
	};
	bool changed;
	int reg;

	/* Sample after sm_step_locked() has completed any hardware writes. */
	reg = sm_read(c, 0x13);
	if (reg < 0)
		state.charger_error = reg;
	else
		state.charger_status = reg & 0x0e; /* ONLINE and CHG_STAT only */
	state.battery_error = sm_psy_int(c->battery, POWER_SUPPLY_PROP_STATUS,
				       &state.battery_status);
	changed = !c->notified_valid || sm_notify_changed(&c->notified, &state);
	c->notified = state;
	c->notified_valid = true;
	return changed;
}

static void sm_poll(struct work_struct *work)''')
replace('''					 struct sm_charger, work);

	mutex_lock(&c->lock);
	if (c->paused) goto out;
	sm_step_locked(c);
	schedule_delayed_work(&c->work, msecs_to_jiffies(1000));
out:
	mutex_unlock(&c->lock);
	power_supply_changed(c->psy);
}''', '''					 struct sm_charger, work);
	bool notify = false;

	mutex_lock(&c->lock);
	if (c->paused) goto out;
	sm_step_locked(c);
	notify = sm_notification_locked(c);
	schedule_delayed_work(&c->work, msecs_to_jiffies(1000));
out:
	mutex_unlock(&c->lock);
	if (notify)
		power_supply_changed(c->psy);
}''')
replace('''	if (!c->battery_name)
		return -EPROBE_DEFER;
	config.supplied_to''', '''	if (!c->battery_name)
		return -EPROBE_DEFER;
	c->battery = power_supply_get_by_name(c->battery_name);
	if (!c->battery)
		return -EPROBE_DEFER;
	ret = devm_add_action_or_reset(dev, sm_put_supply, c->battery);
	if (ret)
		return ret;
	if (c->battery->desc->type != POWER_SUPPLY_TYPE_BATTERY ||
	    c->battery->dev.parent != &c->gauge->dev)
		return -ENODEV;
	config.supplied_to''')
replace('''	c->paused = false;
	mod_delayed_work(system_wq, &c->work, 0);
	mutex_unlock(&c->lock);
	return 0;
}

static void sm_shutdown''', '''	c->paused = false;
	/* The first fresh post-resume sample is always reported. */
	c->notified_valid = false;
	mod_delayed_work(system_wq, &c->work, 0);
	mutex_unlock(&c->lock);
	return 0;
}

static void sm_shutdown''')

(CANDIDATE / LIVE.name).write_text(candidate, newline='\n')
header = (ROOT / 'charging-notify.h').read_text()
(CANDIDATE / 'charging-notify.h').write_text(header, newline='\n')
diff = ''.join(difflib.unified_diff(base.splitlines(True), candidate.splitlines(True),
                                 fromfile='a/samurai-mp2650.c', tofile='b/samurai-mp2650.c'))
diff += ''.join(difflib.unified_diff([], header.splitlines(True),
                                  fromfile='/dev/null', tofile='b/charging-notify.h'))
(ROOT / 'notification-state.patch').write_text(diff, newline='\n')
report = {'scope': 'offline candidate only; no deployment or kernel build',
          'base_sha256': hashlib.sha256(base_path.read_bytes()).hexdigest(),
          'main_source_still_matches_base': LIVE.read_text() == base,
          'candidate_files': {name: hashlib.sha256((CANDIDATE / name).read_bytes()).hexdigest()
                              for name in [LIVE.name, 'charging-notify.h']},
          'patch_sha256': hashlib.sha256((ROOT / 'notification-state.patch').read_bytes()).hexdigest()}
(ROOT / 'notification-candidate.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
