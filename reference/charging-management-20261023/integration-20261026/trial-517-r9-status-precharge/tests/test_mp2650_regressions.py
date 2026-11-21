from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


TRIAL_DIR = Path(__file__).resolve().parents[1]
SOURCE_ROOT = TRIAL_DIR / "source-snapshot" / "drivers" / "power" / "supply"
CHARGER_SOURCE = SOURCE_ROOT / "samurai-mp2650.c"


def _extract_function(text: str, signature: str) -> str:
    start = text.index(signature)
    brace = text.index("{", start)
    depth = 0
    for offset in range(brace, len(text)):
        if text[offset] == "{":
            depth += 1
        elif text[offset] == "}":
            depth -= 1
            if depth == 0:
                return text[start : offset + 1]
    raise AssertionError(f"unterminated function: {signature}")


def _wsl_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    return f"/mnt/{drive}/{resolved.as_posix().split(':', 1)[1].lstrip('/')}"


OEM_FULL_CURRENT_HARNESS = r"""
#include <stdio.h>

#include "oem-full-cycle.h"

#define CHECK(condition) do { \
	if (!(condition)) { \
		fprintf(stderr, "%s:%d: check failed: %s\n", \
			__FILE__, __LINE__, #condition); \
		return 1; \
	} \
} while (0)

int main(void)
{
	struct sm_oem_full_state state;
	struct sm_oem_full_result result = { 0 };
	struct sm_oem_full_sample sample = {
		.valid = 1,
		.source_known = 1,
		.online = 1,
		.protection_good = 1,
		.policy_good = 1,
		.temp_decic = 250,
		.max_cell_uv = 4400000,
		.gauge_current_ua = -2000000,
		.cell_target_uv = 4400000,
		.policy_band_valid = 1,
		.policy_band = 4,
	};
	int tick;

	CHECK(!sm_oem_full_current_qualifies(-2000000));
	CHECK(sm_oem_full_current_qualifies(-110000));
	CHECK(sm_oem_full_current_qualifies(110000));
	CHECK(!sm_oem_full_current_qualifies(111000));
	sm_oem_full_init(&state);
	sample.hardware_full = 1;
	result = sm_oem_full_step(&state, SM_FULL_TICK_NS, &sample);
	CHECK(!result.full);
	CHECK(!result.entered_full);
	CHECK(!result.hold_charge_only);
	CHECK(!state.full);

	sample.hardware_full = 0;
	sample.max_cell_uv = 4420000;
	sm_oem_full_init(&state);
	for (tick = 1; tick <= 11; tick++)
		result = sm_oem_full_step(
			&state, (sm_full_ns)tick * SM_FULL_TICK_NS, &sample);

	/* A discharging node must never satisfy the software-Full current gate,
	 * even when cell voltage remains in the software-Full voltage window.
	 */
	CHECK(!result.stop_all);
	CHECK(!result.full);
	CHECK(!result.entered_full);
	CHECK(!result.hold_charge_only);
	CHECK(!state.full);
	CHECK(state.sw_count == 0);
	return 0;
}
"""


NEGOTIATED_INPUT_HARNESS = r"""
#include <errno.h>
#include <stdio.h>

#define POWER_SUPPLY_USB_TYPE_C 4
#define POWER_SUPPLY_USB_TYPE_PD 5
#define POWER_SUPPLY_USB_TYPE_PD_PPS 6
#define POWER_SUPPLY_USB_TYPE_PD_SPR_AVS 7
#define POWER_SUPPLY_USB_TYPE_PD_PPS_SPR_AVS 8

#include "negotiated-input.h"

#define CHECK(condition) do { \
	if (!(condition)) { \
		fprintf(stderr, "%s:%d: check failed: %s\n", \
			__FILE__, __LINE__, #condition); \
		return 1; \
	} \
} while (0)

static struct sm_input_allowance allowance(int type, int online, int voltage_uv)
{
	return (struct sm_input_allowance){
		.online = online,
		.usb_type = type,
		.voltage_uv = voltage_uv,
		.maximum_ua = 900000,
		.operating_ua = 500000,
	};
}

int main(void)
{
	const int types[] = {
		POWER_SUPPLY_USB_TYPE_PD,
		POWER_SUPPLY_USB_TYPE_PD_PPS,
		POWER_SUPPLY_USB_TYPE_PD_SPR_AVS,
		POWER_SUPPLY_USB_TYPE_PD_PPS_SPR_AVS,
	};
	unsigned int i;

	for (i = 0; i < sizeof(types) / sizeof(types[0]); i++) {
		struct sm_input_allowance high = allowance(types[i], 1, 9000000);
		struct sm_input_allowance five = allowance(types[i], 1, 5000000);

		/* This driver is deliberately 5 V-only. A negotiated type never
		 * turns a 9 V source-PSY allowance into permission to charge.
		 */
		CHECK(sm_typec_allowance_current(&high) == -EPROTO);
		CHECK(sm_typec_allowance_current(&five) == 500000);
	}
	return 0;
}
"""


CYCLE_BOUNDARY_HARNESS = r"""
#include <stdio.h>

#include "charge-cycle.h"

#define CHECK(condition) do { \
	if (!(condition)) { \
		fprintf(stderr, "%s:%d: check failed: %s\n", \
			__FILE__, __LINE__, #condition); \
		return 1; \
	} \
} while (0)

#define SECOND_NS 1000000000ULL

int main(void)
{
	struct sm_charge_cycle cycle;
	sm_cycle_ns rollback;

	sm_cycle_init(&cycle, 0);
	CHECK(sm_cycle_update(&cycle, 0, 1, 0) == 0);
	CHECK(cycle.attached == 1);
	CHECK(sm_cycle_update(&cycle, 35999ULL * SECOND_NS, 1, 0) == 35999);
	CHECK(!cycle.timed_out);
	CHECK(sm_cycle_update(&cycle, 36000ULL * SECOND_NS, 1, 0) == 36000);
	CHECK(cycle.timed_out);
	CHECK(sm_cycle_update(&cycle, 36001ULL * SECOND_NS, 1, 1) == 36000);
	CHECK(cycle.timed_out);

	/* Full is evaluated before elapsed time on an otherwise healthy sample.
	 * It therefore starts a fresh period even at the boundary tick.
	 */
	sm_cycle_init(&cycle, 0);
	CHECK(sm_cycle_update(&cycle, 0, 1, 0) == 0);
	CHECK(sm_cycle_update(&cycle, 36000ULL * SECOND_NS, 1, 1) == 0);
	CHECK(!cycle.timed_out);
	CHECK(cycle.anchor_ns == 36000ULL * SECOND_NS);

	/* Only an independently agreed physical detach clears the timeout. */
	CHECK(sm_cycle_update(&cycle, 36001ULL * SECOND_NS, 1, 0) == 1);
	CHECK(sm_cycle_update(&cycle, 36002ULL * SECOND_NS, 0, 0) == 0);
	CHECK(!cycle.timed_out);
	CHECK(!cycle.attached);

	/* Bad time input fails closed and cannot underflow the timer. */
	sm_cycle_init(&cycle, 10 * SECOND_NS);
	cycle.attached = 1;
	cycle.anchor_ns = 0;
	rollback = 9 * SECOND_NS;
	CHECK(sm_cycle_update(&cycle, rollback, 1, 0) == SM_CYCLE_LIMIT_SECONDS);
	CHECK(cycle.timed_out);
	return 0;
}
"""


def _driver_logic_harness() -> str:
    suspend_needs_stop = _extract_function(
        CHARGER_SOURCE.read_text(),
        "static bool sm_suspend_needs_stop(const struct sm_charger *c)",
    )
    step_locked = _extract_function(
        CHARGER_SOURCE.read_text(),
        "static int sm_step_locked(struct sm_charger *c)",
    )
    return rf"""
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "mp2650-core.h"
#include "charge-cycle-hold.h"
#include "oem-full-cycle.h"
#include "reattach-observation.h"

typedef uint64_t ktime_t;
typedef uint64_t u64;

struct device {{ int unused; }};
struct fake_client {{ struct device dev; }};

struct sm_charger {{
	struct fake_client *client;
	struct sm_io io;
	struct sm_reattach_observation reattach;
	struct sm_sample sample;
	struct sm_target target;
	int cell_ceiling_uv, current_cap_ua, input_cap_ua;
	int last_error, stop_error;
	bool auto_requested, latched, paused, sample_full;
	bool timer_hold_confirmed;
	u64 timer_hold_since_ns;
	bool source_inhibit;
	ktime_t sampled_at;
	struct sm_charge_cycle cycle;
	struct sm_oem_full_state full_state;
	struct sm_oem_full_result full_result;
	bool full_holding, hold_requested, gauge_charge_stop;
	struct sm_thermal_state thermal;
	enum sm_policy_reason thermal_reason;
}};

static bool control = true;
static u64 now_ns;
static int collect_ret;
static struct sm_sample collect_sample;
static unsigned int warning_calls;
static struct fake_client fake_client;

static ktime_t ktime_get_boottime(void)
{{
	return now_ns;
}}

static u64 ktime_get_boottime_ns(void)
{{
	return now_ns;
}}

static int sm_collect(struct sm_charger *c, struct sm_sample *sample)
{{
	(void)c;
	*sample = collect_sample;
	return collect_ret;
}}

static void sm_battery_status_locked(struct sm_charger *c)
{{
	(void)c;
}}

#define dev_warn_ratelimited(dev, format, ...) do {{ \
	(void)(dev); \
	(void)(format); \
	warning_calls++; \
}} while (0)

struct fake_io {{
	int reg[256];
	int fail_all;
	int fail_hold_unpause;
}};

static int fake_read(void *ctx, unsigned int reg)
{{
	struct fake_io *fake = ctx;

	if (fake->fail_all)
		return -EIO;
	if (reg >= 256)
		return -EINVAL;
	return fake->reg[reg];
}}

static int fake_write(void *ctx, unsigned int reg, unsigned int value)
{{
	struct fake_io *fake = ctx;

	if (fake->fail_all)
		return -EIO;
	if (reg >= 256)
		return -EINVAL;
	if (fake->fail_hold_unpause && reg == 0x08 && value == 0x06)
		return -EIO;
	fake->reg[reg] = value;
	return 0;
}}

{suspend_needs_stop}

{step_locked}

#define CHECK(condition) do {{ \
	if (!(condition)) {{ \
		fprintf(stderr, "%s:%d: check failed: %s\n", \
			__FILE__, __LINE__, #condition); \
		return 1; \
	}} \
}} while (0)

static void fake_configure(struct fake_io *fake)
{{
	memset(fake, 0, sizeof(*fake));
	fake->reg[0x00] = 0x0a;
	fake->reg[0x0f] = 0x0a;
	fake->reg[0x02] = 0x16;
	fake->reg[0x03] = 0x91;
	fake->reg[0x04] = 0x6e;
	fake->reg[0x05] = 0x00;
	fake->reg[0x07] = 0x04;
	fake->reg[0x08] = 0x16;
	fake->reg[0x09] = 0x48;
}}

static void reset_charger(struct sm_charger *charger, struct fake_io *fake,
			  u64 start_ns)
{{
	memset(charger, 0, sizeof(*charger));
	fake_configure(fake);
	charger->io = (struct sm_io){{
		.ctx = fake,
		.read = fake_read,
		.write = fake_write,
	}};
	charger->client = &fake_client;
	charger->auto_requested = true;
	charger->cell_ceiling_uv = 4400000;
	charger->current_cap_ua = 1100000;
	charger->input_cap_ua = 500000;
	sm_oem_full_init(&charger->full_state);
	sm_cycle_init(&charger->cycle, start_ns);
	charger->cycle.attached = 1;
	charger->cycle.anchor_ns = start_ns;
	charger->cycle.last_ns = start_ns;
	now_ns = start_ns;
	collect_ret = 0;
	warning_calls = 0;
}}

static int invalid_online_sample_does_not_touch_thermal(void)
{{
	struct sm_charger charger;
	struct fake_io fake;
	struct sm_thermal_state before;

	reset_charger(&charger, &fake, 1000000000ULL);
	sm_thermal_init(&charger.thermal);
	charger.thermal.band = 4;
	charger.thermal.pre_shake = 250;
	charger.thermal.hold = SM_THERMAL_NONE;
	before = charger.thermal;
	collect_ret = -EIO;
	collect_sample = (struct sm_sample){{
		.valid = 0,
		.online = 1,
		.protection_ok = 0,
		.temp_decic = 0,
	}};
	now_ns = 2000000000ULL;

	(void)sm_step_locked(&charger);
	CHECK(memcmp(&before, &charger.thermal, sizeof(before)) == 0);
	return 0;
}}

static struct sm_sample normal_sample(int current_ua, int cell_uv)
{{
	return (struct sm_sample){{
		.valid = 1,
		.online = 1,
		.protection_ok = 1,
		.budget_ua = 500000,
		.temp_decic = 250,
		.pack_uv = cell_uv * 2,
		.cell1_uv = cell_uv,
		.cell2_uv = cell_uv,
		.gauge_flags = 0,
		.fault = 0,
		.gauge_current_ua = current_ua,
	}};
}}

static int software_full_cycle(int fail_hold)
{{
	struct sm_charger charger;
	struct fake_io fake;
	sm_cycle_ns original_anchor;
	int ret = 0;
	int tick;

	reset_charger(&charger, &fake, 0);
	collect_sample = normal_sample(100000, 4400000);
	original_anchor = charger.cycle.anchor_ns;

	for (tick = 1; tick <= 6; tick++) {{
		now_ns = (u64)tick * SM_FULL_TICK_NS;
		if (tick == 6 && fail_hold)
			fake.fail_hold_unpause = 1;
		ret = sm_step_locked(&charger);
	}}

	CHECK(charger.full_state.full);
	CHECK(charger.full_result.entered_full);
	CHECK(!charger.cycle.timed_out);
	if (fail_hold) {{
		CHECK(ret == -EIO);
		CHECK(charger.cycle.anchor_ns == original_anchor);
		CHECK(charger.cycle.seconds != 0);
	}} else {{
		CHECK(ret == 0);
		CHECK(charger.cycle.anchor_ns == now_ns);
		CHECK(charger.cycle.seconds == 0);
	}}
	return 0;
}}

static int recharge_cycle(int fail_apply)
{{
	struct sm_charger charger;
	struct fake_io fake;
	sm_cycle_ns original_anchor;
	int ret;

	reset_charger(&charger, &fake, 0);
	collect_sample = normal_sample(50000, 4250000);
	charger.full_state.full = 1;
	charger.full_state.cause = SM_FULL_SOFTWARE;
	charger.full_state.band = 4;
	charger.full_state.recharge_count = 5;
	original_anchor = charger.cycle.anchor_ns;
	fake.fail_all = fail_apply;
	now_ns = 30 * SM_FULL_TICK_NS;

	ret = sm_step_locked(&charger);
	CHECK(charger.full_result.recharge);
	CHECK(!charger.full_state.full);
	CHECK(!charger.cycle.timed_out);
	if (fail_apply) {{
		CHECK(ret == -EIO);
		CHECK(charger.cycle.anchor_ns == original_anchor);
		CHECK(charger.cycle.seconds != 0);
	}} else {{
		CHECK(ret == 0);
		CHECK(charger.cycle.anchor_ns == now_ns);
		CHECK(charger.cycle.seconds == 0);
	}}
	return 0;
}}

static int manual_inhibit_keeps_cycle(void)
{{
	struct sm_charger charger;
	struct fake_io fake;
	sm_cycle_ns original_anchor;
	sm_cycle_ns original_last;

	reset_charger(&charger, &fake, 0);
	collect_sample = normal_sample(100000, 4400000);
	charger.auto_requested = false;
	charger.sample_full = 1;
	charger.full_state.full = 1;
	charger.full_state.cause = SM_FULL_SOFTWARE;
	charger.full_state.band = 4;
	charger.cycle.anchor_ns = 10 * SM_FULL_TICK_NS;
	charger.cycle.last_ns = 10 * SM_FULL_TICK_NS;
	original_anchor = charger.cycle.anchor_ns;
	original_last = charger.cycle.last_ns;
	now_ns = 12 * SM_FULL_TICK_NS;

	(void)sm_step_locked(&charger);
	CHECK(!charger.auto_requested);
	CHECK(charger.full_result.full);
	CHECK(!charger.full_result.hold_charge_only);
	CHECK(charger.cycle.anchor_ns == original_anchor);
	CHECK(charger.cycle.last_ns == now_ns);
	CHECK(charger.cycle.last_ns > original_last);
	return 0;
}}

static int timeout_auto_keeps_cycle(void)
{{
	struct sm_charger charger;
	struct fake_io fake;
	sm_cycle_ns original_anchor;
	int ret;

	reset_charger(&charger, &fake, 0);
	collect_sample = normal_sample(100000, 4250000);
	charger.cycle.anchor_ns = 0;
	charger.cycle.last_ns = 0;
	charger.cycle.attached = 1;
	charger.cycle.timed_out = 1;
	charger.cycle.seconds = SM_CYCLE_LIMIT_SECONDS;
	original_anchor = charger.cycle.anchor_ns;

	now_ns = 1 * SM_FULL_TICK_NS;
	ret = sm_step_locked(&charger);
	CHECK(ret == -ETIME);
	CHECK(charger.latched);
	CHECK(charger.target.enable == 0);
	CHECK(charger.sample.session_seconds == SM_OEM_MAX_SECONDS);
	CHECK(charger.cycle.timed_out);
	CHECK(charger.cycle.anchor_ns == original_anchor);

	charger.auto_requested = false;
	now_ns = 2 * SM_FULL_TICK_NS;
	ret = sm_step_locked(&charger);
	CHECK(ret == -ETIME);
	CHECK(charger.cycle.timed_out);
	CHECK(charger.cycle.anchor_ns == original_anchor);

	charger.auto_requested = true;
	now_ns = 3 * SM_FULL_TICK_NS;
	ret = sm_step_locked(&charger);
	CHECK(ret == -ETIME);
	CHECK(charger.cycle.timed_out);
	CHECK(charger.cycle.anchor_ns == original_anchor);
	CHECK(charger.target.enable == 0);
	return 0;
}}

static int suspend_keeps_only_proven_active_charging(void)
{{
	struct sm_charger charger;
	struct fake_io fake;

	reset_charger(&charger, &fake, 0);
	charger.sample = normal_sample(100000, 4250000);
	charger.target.enable = 1;
	CHECK(!sm_suspend_needs_stop(&charger));

	charger.cycle.timed_out = 1;
	CHECK(sm_suspend_needs_stop(&charger));
	charger.cycle.timed_out = 0;
	charger.latched = 1;
	CHECK(sm_suspend_needs_stop(&charger));
	charger.latched = 0;
	charger.sample.online = 0;
	CHECK(sm_suspend_needs_stop(&charger));
	charger.sample.online = 1;
	charger.sample.protection_ok = 0;
	CHECK(sm_suspend_needs_stop(&charger));
	charger.sample.protection_ok = 1;
	charger.target.enable = 0;
	CHECK(sm_suspend_needs_stop(&charger));
	return 0;
}}

int main(int argc, char **argv)
{{
	if (argc != 2)
		return 2;
	if (!strcmp(argv[1], "invalid-online-thermal"))
		return invalid_online_sample_does_not_touch_thermal();
	if (!strcmp(argv[1], "software-full-io-failure"))
		return software_full_cycle(1);
	if (!strcmp(argv[1], "software-full-success"))
		return software_full_cycle(0);
	if (!strcmp(argv[1], "recharge-io-failure"))
		return recharge_cycle(1);
	if (!strcmp(argv[1], "recharge-success"))
		return recharge_cycle(0);
	if (!strcmp(argv[1], "manual-inhibit-cycle"))
		return manual_inhibit_keeps_cycle();
	if (!strcmp(argv[1], "timeout-auto-cycle"))
		return timeout_auto_keeps_cycle();
	if (!strcmp(argv[1], "suspend-decision"))
		return suspend_keeps_only_proven_active_charging();
	return 2;
}}
"""


def _notifier_harness() -> str:
    source = CHARGER_SOURCE.read_text()
    supply_changed = _extract_function(
        source,
        "static int sm_supply_changed(struct notifier_block *nb,",
    )
    return rf"""
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#define PSY_EVENT_PROP_CHANGED 1UL
#define NOTIFY_DONE 0
#define READ_ONCE(value) (value)
#define container_of(ptr, type, member) \
	((type *)((char *)(ptr) - offsetof(type, member)))

struct power_supply {{ int unused; }};
struct mutex {{ int unused; }};
struct work_struct {{ int unused; }};
struct delayed_work {{ struct work_struct work; }};
struct workqueue_struct {{ int unused; }};
static struct workqueue_struct *system_wq;

struct notifier_block {{
	int (*notifier_call)(struct notifier_block *, unsigned long, void *);
}};

struct sm_charger {{
	struct power_supply *input, *protection, *typec;
	struct mutex lock;
	struct delayed_work work;
	bool paused, full_holding, hold_requested, notified_valid;
	struct notifier_block supply_notifier;
}};

static struct sm_charger *active;
static int lock_depth;
static int clear_calls, clear_lock_depth;
static int schedule_calls, schedule_lock_depth;
static int pause_on_next_lock;

static void mutex_lock(struct mutex *lock)
{{
	(void)lock;
	lock_depth++;
	if (pause_on_next_lock) {{
		pause_on_next_lock = 0;
		active->paused = true;
	}}
}}

static void mutex_unlock(struct mutex *lock)
{{
	(void)lock;
	lock_depth--;
	if (lock_depth < 0) {{
		fprintf(stderr, "mutex unlock underflow\n");
		_exit(1);
	}}
}}

static void sm_clear_full_status_locked(struct sm_charger *charger)
{{
	clear_calls++;
	clear_lock_depth = lock_depth;
	charger->full_holding = false;
	charger->hold_requested = false;
	charger->notified_valid = false;
}}

static bool mod_delayed_work(struct workqueue_struct *wq,
			     struct delayed_work *work, unsigned long delay)
{{
	(void)wq;
	(void)work;
	(void)delay;
	schedule_calls++;
	schedule_lock_depth = lock_depth;
	return true;
}}

{supply_changed}

#define CHECK(condition) do {{ \
	if (!(condition)) {{ \
		fprintf(stderr, "%s:%d: check failed: %s\n", \
			__FILE__, __LINE__, #condition); \
		return 1; \
	}} \
}} while (0)

static struct power_supply input;
static struct power_supply protection;
static struct power_supply typec;
static struct workqueue_struct test_wq;

static void reset_charger(struct sm_charger *charger)
{{
	charger->input = &input;
	charger->protection = &protection;
	charger->typec = &typec;
	charger->paused = false;
	charger->full_holding = true;
	charger->hold_requested = true;
	charger->notified_valid = true;
	active = charger;
	system_wq = &test_wq;
	lock_depth = 0;
	clear_calls = clear_lock_depth = 0;
	schedule_calls = schedule_lock_depth = 0;
	pause_on_next_lock = 0;
}}

static int active_event_clears_and_rearms_under_lock(void)
{{
	struct sm_charger charger;

	reset_charger(&charger);
	(void)sm_supply_changed(
		&charger.supply_notifier, PSY_EVENT_PROP_CHANGED, &input);
	CHECK(clear_calls == 1);
	CHECK(clear_lock_depth == 1);
	CHECK(schedule_calls == 1);
	CHECK(schedule_lock_depth == 1);
	CHECK(!charger.full_holding);
	CHECK(!charger.hold_requested);
	CHECK(!charger.notified_valid);
	CHECK(lock_depth == 0);
	return 0;
}}

static int suspend_race_never_clears_or_rearms(void)
{{
	struct sm_charger charger;

	reset_charger(&charger);
	pause_on_next_lock = 1;
	(void)sm_supply_changed(
		&charger.supply_notifier, PSY_EVENT_PROP_CHANGED, &protection);
	CHECK(charger.paused);
	CHECK(clear_calls == 0);
	CHECK(schedule_calls == 0);
	CHECK(charger.full_holding);
	CHECK(charger.hold_requested);
	CHECK(charger.notified_valid);
	CHECK(lock_depth == 0);
	return 0;
}}

int main(int argc, char **argv)
{{
	if (argc != 2)
		return 2;
	if (!strcmp(argv[1], "active"))
		return active_event_clears_and_rearms_under_lock();
	if (!strcmp(argv[1], "suspend-race"))
		return suspend_race_never_clears_or_rearms();
	return 2;
}}
"""


class Mp2650RegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._temporary.cleanup)
        directory = Path(cls._temporary.name)
        harnesses = {
            "full-current": OEM_FULL_CURRENT_HARNESS,
            "negotiated-input": NEGOTIATED_INPUT_HARNESS,
            "cycle-boundary": CYCLE_BOUNDARY_HARNESS,
            "driver-logic": _driver_logic_harness(),
            "notifier": _notifier_harness(),
        }
        cls.executables: dict[str, Path] = {}
        cls.runner_prefix: list[str] = []

        if os.name == "nt":
            if not shutil.which("wsl.exe"):
                raise unittest.SkipTest("WSL compiler is unavailable")
            cls.runner_prefix = ["wsl.exe", "-e", "bash", "-lc"]
            compiler = "cc"
            include_arg = _wsl_path(SOURCE_ROOT)
        else:
            compiler = shutil.which("cc")
            if not compiler:
                raise unittest.SkipTest("host C compiler is unavailable")
            include_arg = str(SOURCE_ROOT)

        for name, harness in harnesses.items():
            source = directory / f"{name}.c"
            source.write_text(harness)
            executable = directory / f"{name}-test"
            if cls.runner_prefix:
                command = (
                    f"{compiler} -std=c11 -Wall -Wextra -Werror "
                    f"-I {shlex.quote(include_arg)} "
                    f"{shlex.quote(_wsl_path(source))} "
                    f"-o {shlex.quote(_wsl_path(executable))}"
                )
                compile_result = subprocess.run(
                    [*cls.runner_prefix, command],
                    check=False,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                if compile_result.returncode:
                    raise RuntimeError(
                        f"{name} harness compilation failed:\n"
                        f"{compile_result.stdout}{compile_result.stderr}"
                    )
            else:
                compile_result = subprocess.run(
                    [
                        compiler,
                        "-std=c11",
                        "-Wall",
                        "-Wextra",
                        "-Werror",
                        "-I",
                        include_arg,
                        str(source),
                        "-o",
                        str(executable),
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                if compile_result.returncode:
                    raise RuntimeError(
                        f"{name} harness compilation failed:\n"
                        f"{compile_result.stdout}{compile_result.stderr}"
                    )
            cls.executables[name] = executable

    def _run(self, harness: str, case: str | None = None) -> None:
        executable = self.executables[harness]
        if self.runner_prefix:
            command = shlex.quote(_wsl_path(executable))
            if case is not None:
                command += " " + shlex.quote(case)
            result = subprocess.run(
                [*self.runner_prefix, command],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        else:
            args = [str(executable)]
            if case is not None:
                args.append(case)
            result = subprocess.run(
                args,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_large_negative_gauge_current_never_qualifies_software_full(
        self,
    ) -> None:
        self._run("full-current")

    def test_pd_pps_avs_reject_non_five_volt_allowances(self) -> None:
        self._run("negotiated-input")

    def test_invalid_online_sample_does_not_mutate_thermal_hysteresis(
        self,
    ) -> None:
        self._run("driver-logic", "invalid-online-thermal")

    def test_notifier_rechecks_paused_under_lock_and_never_rearms(
        self,
    ) -> None:
        self._run("notifier", "active")
        self._run("notifier", "suspend-race")

    def test_software_full_cycle_reset_waits_for_hold_success(self) -> None:
        self._run("driver-logic", "software-full-io-failure")
        self._run("driver-logic", "software-full-success")

    def test_recharge_cycle_reset_waits_for_apply_success(self) -> None:
        self._run("driver-logic", "recharge-io-failure")
        self._run("driver-logic", "recharge-success")

    def test_manual_inhibit_does_not_reset_an_established_full_cycle(self) -> None:
        self._run("driver-logic", "manual-inhibit-cycle")

    def test_timeout_boundary_and_auto_never_clear_cycle_timeout(self) -> None:
        self._run("cycle-boundary")
        self._run("driver-logic", "timeout-auto-cycle")

    def test_suspend_keeps_only_proven_active_charging(self) -> None:
        source = CHARGER_SOURCE.read_text()
        suspend = _extract_function(
            source, "static int sm_suspend(struct device *dev)"
        )
        self.assertIn("if (sm_suspend_needs_stop(c))", suspend)
        self.assertIn("if (control) ret = sm_stop(&c->io);", suspend)
        self._run("driver-logic", "suspend-decision")


if __name__ == "__main__":
    unittest.main()
