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

# Product policy: battery PSY notifications are deliberately not inputs to the
# charger notifier. sm_battery_status_locked() updates that same PSY, so feeding
# its notification back into sm_supply_changed() could create a Full-hold
# feedback loop. The charger's own poll remains the authority for battery
# presentation refresh; input, protection, and Type-C notifications are the
# events that invalidate a stale Full and wake the charger poll.
BATTERY_PSY_EVENT_POLICY = (
    "Ignore battery PSY changes in sm_supply_changed; only input, protection, "
    "and Type-C changes clear Full and schedule the charger poll."
)


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


def _harness() -> str:
    source = CHARGER_SOURCE.read_text()
    status_evidence = _extract_function(
        source,
        "static void sm_status_evidence(const struct sm_charger *c,",
    )
    battery_status = _extract_function(
        source,
        "static void sm_battery_status_locked(struct sm_charger *c)",
    )
    clear_full = _extract_function(
        source,
        "static void sm_clear_full_status_locked(struct sm_charger *c)",
    )
    supply_changed = _extract_function(
        source,
        "static int sm_supply_changed(struct notifier_block *nb,",
    )
    return rf"""
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#include "samurai-status.h"

#define PSY_EVENT_PROP_CHANGED 1UL
#define NOTIFY_DONE 0
#define READ_ONCE(value) (value)
#define container_of(ptr, type, member) \
	((type *)((char *)(ptr) - offsetof(type, member)))

typedef uint64_t u64;

struct device {{ int unused; }};
struct i2c_client {{ struct device dev; }};
struct power_supply {{ int unused; }};
struct mutex {{ int unused; }};
struct work_struct {{ int unused; }};
struct delayed_work {{ struct work_struct work; }};
struct workqueue_struct {{ int unused; }};
static struct workqueue_struct *system_wq;

struct notifier_block {{
	int (*notifier_call)(struct notifier_block *, unsigned long, void *);
}};

struct sm_sample {{
	int online, valid, protection_ok;
}};

struct sm_charge_cycle {{
	int timed_out;
}};

struct sm_oem_full_state {{
	int full;
}};

struct sm_notify_state {{
	int unused;
}};

struct sm_charger {{
	struct i2c_client *client;
	struct power_supply *input, *protection, *psy, *battery, *typec;
	struct mutex lock;
	struct delayed_work work;
	struct sm_sample sample;
	struct sm_charge_cycle cycle;
	struct sm_oem_full_state full_state;
	bool auto_requested, latched, paused;
	bool source_inhibit;
	int last_error, stop_error;
	bool full_holding, hold_requested, gauge_charge_stop;
	struct notifier_block supply_notifier;
	struct sm_notify_state notified;
	bool notified_valid;
	bool battery_status_bridge;
}};

static bool control;
static int setter_calls;
static int setter_value;
static int setter_ret;
static int setter_seen_full_holding;
static int setter_seen_hold_requested;
static int setter_seen_notified_valid;
static int schedule_calls;
static unsigned long schedule_delay;
static struct workqueue_struct *schedule_wq;
static int lock_depth;
static int warning_calls;
static struct sm_charger *active_charger;

enum test_operation {{
	OP_SETTER = 1,
	OP_SCHEDULE = 2,
}};

static int operation_trace[16];
static int operation_count;

static void record_operation(int operation)
{{
	if (operation_count >= (int)(sizeof(operation_trace) /
					    sizeof(operation_trace[0]))) {{
		fprintf(stderr, "operation trace overflow\n");
		return;
	}}
	operation_trace[operation_count++] = operation;
}}

static void mutex_lock(struct mutex *lock)
{{
	(void)lock;
	lock_depth++;
}}

static void mutex_unlock(struct mutex *lock)
{{
	(void)lock;
	if (--lock_depth < 0) {{
		fprintf(stderr, "mutex unlock underflow\n");
		_exit(1);
	}}
}}

static bool mod_delayed_work(struct workqueue_struct *wq,
			     struct delayed_work *work,
			     unsigned long delay)
{{
	(void)work;
	schedule_calls++;
	schedule_delay = delay;
	schedule_wq = wq;
	record_operation(OP_SCHEDULE);
	return true;
}}

static int bq27xxx_battery_set_status_override(struct power_supply *psy,
					       bool full)
{{
	(void)psy;
	setter_calls++;
	setter_value = full;
	setter_seen_full_holding = active_charger ?
		active_charger->full_holding : -1;
	setter_seen_hold_requested = active_charger ?
		active_charger->hold_requested : -1;
	setter_seen_notified_valid = active_charger ?
		active_charger->notified_valid : -1;
	record_operation(OP_SETTER);
	return setter_ret;
}}

#define dev_warn_ratelimited(dev, format, ...) do {{ \
	(void)(dev); \
	(void)(format); \
	warning_calls++; \
}} while (0)

{status_evidence}

{battery_status}

{clear_full}

{supply_changed}

#define CHECK(condition) do {{ \
	if (!(condition)) {{ \
		fprintf(stderr, "%s:%d: check failed: %s\n", \
			__FILE__, __LINE__, #condition); \
		return 1; \
	}} \
}} while (0)

static struct i2c_client client;
static struct power_supply battery;
static struct power_supply input;
static struct power_supply protection;
static struct power_supply typec;
static struct power_supply unrelated;
static struct workqueue_struct test_workqueue;

static void reset_state(struct sm_charger *charger)
{{
	memset(charger, 0, sizeof(*charger));
	charger->client = &client;
	charger->input = &input;
	charger->protection = &protection;
	charger->typec = &typec;
	charger->battery = &battery;
	charger->battery_status_bridge = true;
	charger->auto_requested = true;
	charger->sample.online = 1;
	charger->sample.valid = 1;
	charger->sample.protection_ok = 1;
	charger->full_state.full = 1;
	charger->full_holding = true;
	charger->hold_requested = true;
	charger->notified_valid = true;
	active_charger = charger;
	system_wq = &test_workqueue;
	setter_calls = 0;
	setter_value = -1;
	setter_ret = 0;
	setter_seen_full_holding = -1;
	setter_seen_hold_requested = -1;
	setter_seen_notified_valid = -1;
	schedule_calls = 0;
	schedule_delay = ~0UL;
	schedule_wq = NULL;
	lock_depth = 0;
	warning_calls = 0;
	operation_count = 0;
}}

static int call_event(struct sm_charger *charger, unsigned long event,
		      void *data)
{{
	return sm_supply_changed(&charger->supply_notifier, event, data);
}}

static int test_valid_supply_events(void)
{{
	void *supplies[] = {{
		&input,
		&protection,
		&typec,
	}};
	unsigned int i;

	for (i = 0; i < sizeof(supplies) / sizeof(supplies[0]); i++) {{
		struct sm_charger charger;

		reset_state(&charger);
		CHECK(call_event(&charger, PSY_EVENT_PROP_CHANGED,
				 supplies[i]) == NOTIFY_DONE);
		CHECK(setter_calls == 1);
		CHECK(setter_value == false);
		CHECK(setter_seen_full_holding == false);
		CHECK(setter_seen_hold_requested == false);
		CHECK(setter_seen_notified_valid == false);
		CHECK(!charger.full_holding);
		CHECK(!charger.hold_requested);
		CHECK(!charger.notified_valid);
		CHECK(schedule_calls == 1);
		CHECK(schedule_delay == 0);
		CHECK(schedule_wq == system_wq);
		CHECK(operation_count == 2);
		CHECK(operation_trace[0] == OP_SETTER);
		CHECK(operation_trace[1] == OP_SCHEDULE);
		CHECK(lock_depth == 0);
		CHECK(warning_calls == 0);
	}}
	return 0;
}}

static int test_ignored_events(void)
{{
	struct sm_charger charger;

	reset_state(&charger);
	charger.paused = true;
	CHECK(call_event(&charger, PSY_EVENT_PROP_CHANGED, &input) == NOTIFY_DONE);
	CHECK(charger.full_holding && charger.hold_requested);
	CHECK(charger.notified_valid);
	CHECK(setter_calls == 0 && schedule_calls == 0);
	CHECK(operation_count == 0 && lock_depth == 0);

	reset_state(&charger);
	CHECK(call_event(&charger, PSY_EVENT_PROP_CHANGED + 1, &input) ==
	      NOTIFY_DONE);
	CHECK(charger.full_holding && charger.hold_requested);
	CHECK(charger.notified_valid);
	CHECK(setter_calls == 0 && schedule_calls == 0);
	CHECK(operation_count == 0 && lock_depth == 0);

	reset_state(&charger);
	CHECK(call_event(&charger, PSY_EVENT_PROP_CHANGED, &unrelated) ==
	      NOTIFY_DONE);
	CHECK(charger.full_holding && charger.hold_requested);
	CHECK(charger.notified_valid);
	CHECK(setter_calls == 0 && schedule_calls == 0);
	CHECK(operation_count == 0 && lock_depth == 0);

	return 0;
}}

static int test_battery_event_is_gated_by_product_policy(void)
{{
	struct sm_charger charger;

	reset_state(&charger);
	CHECK(call_event(&charger, PSY_EVENT_PROP_CHANGED, &battery) ==
	      NOTIFY_DONE);
	CHECK(charger.full_holding && charger.hold_requested);
	CHECK(charger.notified_valid);
	CHECK(setter_calls == 0 && schedule_calls == 0);
	CHECK(operation_count == 0 && lock_depth == 0);
	return 0;
}}

static int test_setter_error_still_invalidates_and_polls(void)
{{
	struct sm_charger charger;

	reset_state(&charger);
	setter_ret = -EIO;
	CHECK(call_event(&charger, PSY_EVENT_PROP_CHANGED, &protection) ==
	      NOTIFY_DONE);
	CHECK(setter_calls == 1 && setter_value == false);
	CHECK(setter_seen_full_holding == false);
	CHECK(setter_seen_hold_requested == false);
	CHECK(setter_seen_notified_valid == false);
	CHECK(!charger.full_holding && !charger.hold_requested);
	CHECK(!charger.notified_valid);
	CHECK(schedule_calls == 1 && schedule_delay == 0);
	CHECK(schedule_wq == system_wq);
	CHECK(operation_count == 2);
	CHECK(operation_trace[0] == OP_SETTER);
	CHECK(operation_trace[1] == OP_SCHEDULE);
	CHECK(warning_calls == 1);
	CHECK(lock_depth == 0);
	return 0;
}}

int main(void)
{{
	control = true;
	if (test_valid_supply_events())
		return 1;
	if (test_ignored_events())
		return 1;
	if (test_battery_event_is_gated_by_product_policy())
		return 1;
	if (test_setter_error_still_invalidates_and_polls())
		return 1;
	return 0;
}}
"""


class NotifierRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._temporary.cleanup)
        directory = Path(cls._temporary.name)
        source = directory / "samurai_notifier_runtime_test.c"
        source.write_text(_harness())
        cls.executable = directory / "samurai_notifier_runtime_test"

        if os.name == "nt":
            if not shutil.which("wsl.exe"):
                raise unittest.SkipTest("WSL compiler is unavailable")
            command = (
                "cc -std=c11 -Wall -Wextra -Werror "
                f"-I {shlex.quote(_wsl_path(SOURCE_ROOT))} "
                f"{shlex.quote(_wsl_path(source))} "
                f"-o {shlex.quote(_wsl_path(cls.executable))}"
            )
            cls.runner_prefix = ["wsl.exe", "-e", "bash", "-lc"]
            subprocess.run(
                [*cls.runner_prefix, command],
                check=True,
                capture_output=True,
                text=True,
            )
        else:
            compiler = shutil.which("cc")
            if not compiler:
                raise unittest.SkipTest("host C compiler is unavailable")
            subprocess.run(
                [
                    compiler,
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-I",
                    str(SOURCE_ROOT),
                    str(source),
                    "-o",
                    str(cls.executable),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            cls.runner_prefix = []

    def test_actual_notifier_policy_and_ordering(self) -> None:
        self.assertIn("Ignore battery PSY changes", BATTERY_PSY_EVENT_POLICY)
        if self.runner_prefix:
            command = shlex.quote(_wsl_path(self.executable))
            result = subprocess.run(
                [*self.runner_prefix, command],
                check=False,
                capture_output=True,
                text=True,
            )
        else:
            result = subprocess.run(
                [str(self.executable)],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
