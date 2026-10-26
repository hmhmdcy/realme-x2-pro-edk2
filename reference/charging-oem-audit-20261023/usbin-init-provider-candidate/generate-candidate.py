"""Generate only the independent R7 provider candidate; never touch baseline."""
from pathlib import Path
import difflib, hashlib
HERE = Path(__file__).resolve().parent
base = (HERE/'baseline-samurai-usb-input.c').read_text()
assert hashlib.sha256((HERE/'baseline-samurai-usb-input.c').read_bytes()).hexdigest() == 'b712764fbd4ab24475ae1ba030ee4c26c7eb048a6038488a5435b44ef7eb7098'
text = base.replace('/* RMX1931 input observer: no PMIC, charger, USB role or PD writes. */',
 '/* RMX1931 input observer; optional off-only USBIN one-bit initialization. */')
text = text.replace('#include <linux/workqueue.h>', '#include <linux/workqueue.h>\n#include <linux/timekeeping.h>')
text = text.replace('#include "samurai-usb-input-decode.h"', '#include "samurai-usb-input-decode.h"\n#include "usbin-init-core.h"')
text = text.replace('static bool native_retained;', 'static bool native_retained;\n/* Internal evidence, never a module parameter. */\nstatic bool native_ref_held;')
text = text.replace('\t\t__module_get(THIS_MODULE);', '\t\t__module_get(THIS_MODULE);\n\t\tnative_ref_held = true;')
text = text.replace('struct samurai_usb_input {', '''/* Experimental opt-in: no automatic production enable before physical review. */
static bool usbin_init;
module_param(usbin_init, bool, 0444);
MODULE_PARM_DESC(usbin_init, "Experimental one-shot off-only USBIN initialization; default disabled");

enum samurai_usbin_stage {
	SUI_DISABLED, SUI_PROBE_ZERO, SUI_WAIT_FIRST_OFF,
	SUI_TRANSACTION, SUI_INITIALIZED, SUI_TERMINAL,
};

struct samurai_usb_input {''')
text = text.replace('\tint udc_current_ua;\n};', '''	int udc_current_ua;
	/* Independent diagnostic history; never changes source/native allowance. */
	enum samurai_usbin_stage init_stage;
	struct ui_state init;
	unsigned int init_probe_before, init_probe_after;
	int init_probe_error;
	unsigned long long init_observed_ms;
	struct ui_snapshot init_observed;
};''')
marker = 'static int samurai_usb_get_budget('
functions = r'''/* All initialization IO uses the provider's existing mutex and PM ordering.
 * No getter writes, restore command, retry loop or additional owner exists.
 */
static unsigned long long samurai_usbin_now(void *ctx)
{
	return ktime_to_ms(ktime_get_boottime());
}

static int samurai_usbin_config(void *ctx, unsigned int *value)
{
	struct samurai_usb_input *input = ctx;
	int ret = regmap_read(input->map, UI_CFG, value);

	if (!ret && *value > 0xff)
		ret = -EIO;
	return ret;
}

static int samurai_usbin_snapshot(void *ctx, struct ui_snapshot *snapshot)
{
	struct samurai_usb_input *input = ctx;
	struct samurai_usb_status status;
	unsigned int cfg;
	int ret = samurai_usb_read_status(input, &status);

	if (ret)
		return ret;
	ret = samurai_usbin_config(input, &cfg);
	if (ret)
		return ret;
	snapshot->raw[0] = status.apsd;
	snapshot->raw[1] = status.result;
	snapshot->raw[2] = status.plugin;
	snapshot->raw[3] = status.cc;
	snapshot->raw[4] = status.attached;
	snapshot->raw[5] = status.misc;
	snapshot->raw[6] = status.legacy;
	snapshot->cfg = cfg;
	return 0;
}

static int samurai_usbin_clear_bit(void *ctx, unsigned int value)
{
	struct samurai_usb_input *input = ctx;

	/* Frozen core also supports restore, but this integration never does. */
	if (value)
		return -EINVAL;
	return regmap_update_bits(input->map, UI_CFG, UI_BIT, 0);
}

static void samurai_usbin_prepare(struct samurai_usb_input *input)
{
	int ret;

	if (!usbin_init)
		return;
	/* A user-supplied native_retained parameter is not proof of a ref.
	 * Only the observed native DT wiring plus the actual retain path may
	 * authorize persistent initialization/error history in this module.
	 */
	if (!native_ref_held) {
		input->init_probe_error = -ENODEV;
		input->init_stage = SUI_TERMINAL;
		ui_terminal(&input->init, UI_ERROR, -ENODEV);
		return;
	}
	ret = samurai_usbin_config(input, &input->init_probe_before);
	if (!ret)
		ret = samurai_usbin_config(input, &input->init_probe_after);
	if (!ret && input->init_probe_before != input->init_probe_after)
		ret = -EAGAIN;
	if (ret) {
		input->init_probe_error = ret;
		input->init_stage = SUI_TERMINAL;
		ui_terminal(&input->init, UI_ERROR, ret);
		return;
	}
	input->init_stage = input->init_probe_after & UI_BIT ?
		SUI_WAIT_FIRST_OFF : SUI_PROBE_ZERO;
}

static void samurai_usbin_step_locked(struct samurai_usb_input *input)
{
	const struct ui_ops io = {
		.ctx = input, .snapshot = samurai_usbin_snapshot,
		.config = samurai_usbin_config, .write_bit = samurai_usbin_clear_bit,
		.now_ms = samurai_usbin_now,
	};
	int ret;

	if (input->paused)
		return;
	if (input->init_stage == SUI_WAIT_FIRST_OFF) {
		ret = samurai_usbin_snapshot(input, &input->init_observed);
		input->init_observed_ms = samurai_usbin_now(input);
		if (ret) {
			input->init_stage = SUI_TERMINAL;
			ui_terminal(&input->init, UI_ERROR, ret);
			return;
		}
		if (!ui_off(&input->init_observed))
			return;
		ret = ui_start(&input->init, UI_CLEAR, input->init_observed_ms);
		if (ret) {
			input->init_stage = SUI_TERMINAL;
			ui_terminal(&input->init, UI_ERROR, ret);
			return;
		}
		input->init_stage = SUI_TRANSACTION;
	}
	if (input->init_stage != SUI_TRANSACTION)
		return;
	/* Keep the existing 1000ms poll. The core's >=500ms stable-off gate
	 * and <=250ms fresh prewrite gate have distinct meanings.
	 */
	ui_step(&input->init, &io, samurai_usbin_now(input));
	if (input->init.running)
		return;
	if (input->init.phase == UI_CLEAR_VERIFIED && !ui_commit(&input->init))
		input->init_stage = SUI_INITIALIZED;
	else
		input->init_stage = SUI_TERMINAL;
}

static ssize_t usbin_init_state_show(struct device *dev,
				    struct device_attribute *attr, char *buf)
{
	static const char * const stages[] = {
		"disabled", "probe_already_zero", "wait_first_off",
		"transaction", "initialized", "terminal",
	};
	struct samurai_usb_input *input = dev_get_drvdata(dev);
	struct ui_state *s = &input->init;
	ssize_t ret;

	/* Cached observation only: status reads cannot advance the transaction. */
	mutex_lock(&input->lock);
	ret = sysfs_emit(buf,
		"{\"schema\":1,\"enabled\":%u,\"stage\":\"%s\",\"paused\":%u,\"native_ref_held\":%u,"
		"\"now_ms\":%llu,\"probe_before\":%u,\"probe_after\":%u,\"probe_error\":%d,"
		"\"observed_ms\":%llu,\"observed_raw\":\"%*phN\",\"observed_cfg\":%u,"
		"\"phase\":%u,\"running\":%u,\"clear_used\":%u,\"started_ms\":%llu,\"deadline_ms\":%llu,"
		"\"first_ms\":%llu,\"off_samples\":%u,\"pre_started_ms\":%llu,\"prewrite_ms\":%llu,\"post_ms\":%llu,"
		"\"old_valid\":%u,\"old_bit\":%u,\"before_cfg\":%u,\"after_cfg\":%u,"
		"\"write_attempted\":%u,\"write_return\":%d,\"readback_error\":%d,\"post_error\":%d,\"error\":%d,"
		"\"pending_restore\":%u,\"unknown_write\":%u,\"changed\":%u,\"committed\":%u,"
		"\"pre_raw\":\"%*phN\",\"pre_cfg\":%u,\"post_raw\":\"%*phN\",\"post_cfg\":%u}\n",
		input->init_stage != SUI_DISABLED, stages[input->init_stage], input->paused, native_ref_held,
		samurai_usbin_now(input), input->init_probe_before, input->init_probe_after,
		input->init_probe_error, input->init_observed_ms, 7, input->init_observed.raw,
		input->init_observed.cfg, s->phase, s->running, s->clear_used,
		s->started_ms, s->deadline_ms, s->first_ms, s->off_samples,
		s->pre_started_ms, s->prewrite_ms, s->post_ms,
		s->old_valid, s->old_bit, s->before_cfg, s->after_cfg,
		s->write_attempted, s->write_return, s->readback_error, s->post_error, s->error,
		s->pending_restore, s->unknown_write, s->changed, s->committed,
		7, s->pre.raw, s->pre.cfg, 7, s->post.raw, s->post.cfg);
	mutex_unlock(&input->lock);
	return ret;
}
static DEVICE_ATTR_RO(usbin_init_state);
static struct attribute *samurai_usbin_attrs[] = {
	&dev_attr_usbin_init_state.attr, NULL,
};
ATTRIBUTE_GROUPS(samurai_usbin);

'''
assert text.count(marker) == 1
text = text.replace(marker, functions+marker)
needle = '\tif (!input->paused)\n\t\tschedule_delayed_work(&input->work, msecs_to_jiffies(1000));'
assert text.count(needle) == 1
text = text.replace(needle, '\tsamurai_usbin_step_locked(input);\n'+needle)
needle = '\tinput->paused = true;\n\tinput->udc_valid = false;'
assert text.count(needle) == 1
text = text.replace(needle, needle+'''
	/* An unstarted wait survives suspend; an active absolute deadline does
	 * not restart or extend after resume. Preserve all terminal history.
	 */
	if (input->init_stage == SUI_TRANSACTION && input->init.running) {
		ui_terminal(&input->init, UI_CANCELLED, -ECANCELED);
		input->init_stage = SUI_TERMINAL;
	}''')
needle = '\tschedule_delayed_work(&input->work, 0);\n\tsamurai_usb_retain_for_native_consumer(dev);'
assert text.count(needle)==1
text = text.replace(needle, '\tsamurai_usb_retain_for_native_consumer(dev);\n\tmutex_lock(&input->lock);\n\tsamurai_usbin_prepare(input);\n\tmutex_unlock(&input->lock);\n\tschedule_delayed_work(&input->work, 0);')
text = text.replace('\t\t.suppress_bind_attrs = true,', '\t\t.suppress_bind_attrs = true,\n\t\t.dev_groups = samurai_usbin_groups,')
text = text.replace('dev_info(dev, "read-only PM8150B USB input budget registered\\n");',
 'dev_info(dev, "PM8150B USB input budget registered (USBIN init opt-in %u)\\n", usbin_init);')
text = text.replace('MODULE_DESCRIPTION("RMX1931 read-only PM8150B USB input budget observer");',
 'MODULE_DESCRIPTION("RMX1931 PM8150B USB input observer with optional off-only initialization");')
(HERE/'samurai-usb-input.c').write_text(text)
(HERE/'provider-init.patch').write_text(''.join(difflib.unified_diff(base.splitlines(True),text.splitlines(True),fromfile='a/drivers/power/supply/samurai-usb-input.c',tofile='b/drivers/power/supply/samurai-usb-input.c')))
print('candidate generated; baseline, decoder and core unchanged')
