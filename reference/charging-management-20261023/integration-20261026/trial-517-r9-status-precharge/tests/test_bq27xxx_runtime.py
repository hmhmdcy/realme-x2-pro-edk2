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
BQ_SOURCE = SOURCE_ROOT / "bq27xxx_battery.c"


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
    source = BQ_SOURCE.read_text()
    expire = _extract_function(
        source, "static void bq27xxx_full_status_expire(struct work_struct *work)"
    )
    setter = _extract_function(
        source,
        "int bq27xxx_battery_set_status_override(struct power_supply *bat, bool full)",
    )
    teardown = _extract_function(
        source, "void bq27xxx_battery_teardown(struct bq27xxx_device_info *di)"
    )
    suspend = _extract_function(
        source, "static int bq27xxx_battery_suspend(struct device *dev)"
    )
    resume = _extract_function(
        source, "static int bq27xxx_battery_resume(struct device *dev)"
    )
    return rf"""
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#include "bq27xxx-status-policy.h"

#define EXPORT_SYMBOL_GPL(symbol)
#define time_after_eq(a, b) ((long)((b) - (a)) <= 0)
#define container_of(ptr, type, member) \
	((type *)((char *)(ptr) - offsetof(type, member)))

typedef uint32_t u32;

struct work_struct {{ int unused; }};
struct delayed_work {{ struct work_struct work; }};
struct workqueue_struct;
struct mutex {{ int unused; }};
struct list_head {{ int unused; }};
struct device {{ int unused; }};
struct power_supply;

struct power_supply_desc {{
	int (*get_property)(struct power_supply *psy, int prop, void *value);
}};

struct power_supply {{
	struct power_supply_desc *desc;
}};

struct bq27xxx_device_info {{
	bool removed;
	bool suspended;
	struct delayed_work work;
	struct delayed_work full_status_work;
	struct power_supply *bat;
	struct mutex lock;
	struct list_head list;
	unsigned long full_status_deadline;
	u32 full_status_generation;
	bool full_status_override;
	bool samurai;
}};

static unsigned long jiffies = 1000;
static struct bq27xxx_device_info *active_di;
static struct workqueue_struct *system_wq;
static struct mutex bq27xxx_list_lock;
static int changes;
static int schedules;
static int cancels;
static int normal_schedules;
static int normal_schedule_lock_depth = -1;
static int normal_cancel_syncs;
static int full_cancel_syncs;
static int list_deletes;
static int lock_depth;
static int last_mod_delay = -1;
static bool delay_next_lock;
static unsigned long next_lock_delay;
static char sync_cancel_order[8];
static size_t sync_cancel_order_len;

static unsigned long msecs_to_jiffies(unsigned int milliseconds)
{{
	return milliseconds / 1000;
}}

static bool mod_delayed_work(struct workqueue_struct *wq,
			     struct delayed_work *work,
			     unsigned long delay)
{{
	(void)wq;
	(void)work;
	last_mod_delay = delay;
	schedules++;
	return true;
}}

static bool cancel_delayed_work(struct delayed_work *work)
{{
	(void)work;
	cancels++;
	return true;
}}

static bool cancel_delayed_work_sync(struct delayed_work *work)
{{
	if (work == &active_di->work) {{
		normal_cancel_syncs++;
		sync_cancel_order[sync_cancel_order_len++] = 'p';
	}} else if (work == &active_di->full_status_work) {{
		full_cancel_syncs++;
		sync_cancel_order[sync_cancel_order_len++] = 'f';
	}} else {{
		fprintf(stderr, "unexpected delayed work canceled\n");
		_exit(1);
	}}
	return true;
}}

static bool schedule_delayed_work(struct delayed_work *work,
				  unsigned long delay)
{{
	(void)delay;
	if (work != &active_di->work) {{
		fprintf(stderr, "unexpected delayed work scheduled\n");
		_exit(1);
	}}
	normal_schedules++;
	normal_schedule_lock_depth = lock_depth;
	return true;
}}

static void power_supply_changed(struct power_supply *psy)
{{
	(void)psy;
	changes++;
}}

static void *dev_get_drvdata(struct device *dev)
{{
	(void)dev;
	return active_di;
}}

static void *power_supply_get_drvdata(struct power_supply *psy)
{{
	(void)psy;
	return active_di;
}}

static void list_del(struct list_head *entry)
{{
	(void)entry;
	list_deletes++;
}}

static bool bq27xxx_samurai_instant(struct bq27xxx_device_info *di)
{{
	return di->samurai;
}}

static void mutex_lock(struct mutex *lock)
{{
	(void)lock;
	if (delay_next_lock) {{
		jiffies += next_lock_delay;
		delay_next_lock = false;
	}}
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

static int bq27xxx_battery_get_property(struct power_supply *psy, int prop,
					void *value)
{{
	(void)psy;
	(void)prop;
	(void)value;
	return 0;
}}

{expire}

{setter}

{teardown}

{suspend}

{resume}

#define CHECK(condition) do {{ \
	if (!(condition)) {{ \
		fprintf(stderr, "%s:%d: check failed: %s\n", \
			__FILE__, __LINE__, #condition); \
		return 1; \
	}} \
}} while (0)

static void reset_state(void)
{{
	struct power_supply *bat = active_di->bat;
	memset(active_di, 0, sizeof(*active_di));
	active_di->bat = bat;
	active_di->samurai = true;
	jiffies = 1000;
	changes = 0;
	schedules = 0;
	cancels = 0;
	normal_schedules = 0;
	normal_schedule_lock_depth = -1;
	normal_cancel_syncs = 0;
	full_cancel_syncs = 0;
	list_deletes = 0;
	lock_depth = 0;
	last_mod_delay = -1;
	delay_next_lock = false;
	next_lock_delay = 0;
	memset(sync_cancel_order, 0, sizeof(sync_cancel_order));
	sync_cancel_order_len = 0;
}}

static int run_setter_expiry(void)
{{
	u32 generation;

	reset_state();
	CHECK(bq27xxx_battery_set_status_override(active_di->bat, true) == 0);
	CHECK(active_di->full_status_override);
	CHECK(active_di->full_status_deadline == jiffies + 4);
	CHECK(active_di->full_status_generation == 1);
	CHECK(changes == 1 && schedules == 1 && cancels == 0 && lock_depth == 0);

	reset_state();
	delay_next_lock = true;
	next_lock_delay = 10;
	CHECK(bq27xxx_battery_set_status_override(active_di->bat, true) == 0);
	CHECK(jiffies == 1010);
	CHECK(active_di->full_status_deadline == 1014);
	CHECK(bq27xxx_full_status_active(
		      active_di->full_status_override,
		      active_di->full_status_deadline, jiffies));
	CHECK(last_mod_delay == 4);
	CHECK(changes == 1 && schedules == 1 && lock_depth == 0);

	generation = active_di->full_status_generation;
	jiffies++;
	CHECK(bq27xxx_battery_set_status_override(active_di->bat, true) == 0);
	CHECK(active_di->full_status_generation == generation);
	CHECK(changes == 1 && schedules == 2 && lock_depth == 0);
	CHECK(active_di->full_status_deadline == jiffies + 4);

	jiffies = active_di->full_status_deadline - 1;
	bq27xxx_full_status_expire(&active_di->full_status_work.work);
	CHECK(active_di->full_status_override && changes == 1);

	jiffies = active_di->full_status_deadline;
	bq27xxx_full_status_expire(&active_di->full_status_work.work);
	CHECK(!active_di->full_status_override);
	CHECK(active_di->full_status_deadline == 0);
	CHECK(active_di->full_status_generation == generation + 1);
	CHECK(changes == 2 && lock_depth == 0);

	reset_state();
	CHECK(bq27xxx_battery_set_status_override(active_di->bat, true) == 0);
	jiffies += 10;
	CHECK(bq27xxx_battery_set_status_override(active_di->bat, false) == 0);
	CHECK(!active_di->full_status_override &&
	      active_di->full_status_deadline == 0);
	CHECK(changes == 2 && cancels == 1 && lock_depth == 0);

	reset_state();
	CHECK(bq27xxx_battery_set_status_override(active_di->bat, true) == 0);
	jiffies += 10;
	CHECK(bq27xxx_battery_set_status_override(active_di->bat, true) == 0);
	CHECK(active_di->full_status_override);
	CHECK(changes == 2 && schedules == 2 && lock_depth == 0);

	reset_state();
	active_di->suspended = true;
	CHECK(bq27xxx_battery_set_status_override(active_di->bat, true) ==
	      -ESHUTDOWN);
	CHECK(!active_di->full_status_override &&
	      changes == 0 && schedules == 0);
	CHECK(lock_depth == 0);

	reset_state();
	active_di->removed = true;
	CHECK(bq27xxx_battery_set_status_override(active_di->bat, true) ==
	      -ESHUTDOWN);
	CHECK(!active_di->full_status_override &&
	      changes == 0 && schedules == 0);
	CHECK(lock_depth == 0);

	return 0;
}}

static int run_lifecycle(struct device *dev)
{{
	u32 generation;
	int normal_schedules_before_resume;

	reset_state();
	CHECK(bq27xxx_battery_set_status_override(active_di->bat, true) == 0);
	generation = active_di->full_status_generation;

	CHECK(bq27xxx_battery_suspend(dev) == 0);
	CHECK(active_di->suspended && !active_di->removed);
	CHECK(!active_di->full_status_override);
	CHECK(active_di->full_status_deadline == 0);
	CHECK(active_di->full_status_generation == generation + 1);
	CHECK(normal_cancel_syncs == 1 && full_cancel_syncs == 1);
	CHECK(strcmp(sync_cancel_order, "pf") == 0);
	CHECK(changes == 1 && schedules == 1 && cancels == 0);
	CHECK(lock_depth == 0);

	CHECK(bq27xxx_battery_set_status_override(active_di->bat, true) ==
	      -ESHUTDOWN);
	CHECK(!active_di->full_status_override);
	CHECK(active_di->full_status_generation == generation + 1);
	CHECK(changes == 1 && schedules == 1 && normal_schedules == 0);
	CHECK(lock_depth == 0);

	CHECK(bq27xxx_battery_resume(dev) == 0);
	CHECK(!active_di->suspended && !active_di->removed);
	CHECK(!active_di->full_status_override);
	CHECK(active_di->full_status_deadline == 0);
	CHECK(active_di->full_status_generation == generation + 1);
	CHECK(normal_schedules == 1 && schedules == 1);
	CHECK(normal_schedule_lock_depth == 1);
	CHECK(lock_depth == 0);

	CHECK(bq27xxx_battery_set_status_override(active_di->bat, true) == 0);
	generation = active_di->full_status_generation;
	CHECK(active_di->full_status_override);
	CHECK(changes == 2 && schedules == 2);

	normal_schedules_before_resume = normal_schedules;
	bq27xxx_battery_teardown(active_di);
	CHECK(active_di->removed && active_di->suspended);
	CHECK(!active_di->full_status_override);
	CHECK(active_di->full_status_deadline == 0);
	CHECK(active_di->full_status_generation == generation + 1);
	CHECK(normal_cancel_syncs == 2 && full_cancel_syncs == 2);
	CHECK(strcmp(sync_cancel_order, "pfpf") == 0);
	CHECK(list_deletes == 1);
	CHECK(changes == 2 && schedules == 2);
	CHECK(lock_depth == 0);

	CHECK(bq27xxx_battery_set_status_override(active_di->bat, true) ==
	      -ESHUTDOWN);
	CHECK(active_di->full_status_generation == generation + 1);
	CHECK(bq27xxx_battery_resume(dev) == 0);
	CHECK(active_di->removed && active_di->suspended);
	CHECK(!active_di->full_status_override);
	CHECK(normal_schedules == normal_schedules_before_resume);
	CHECK(schedules == 2 && lock_depth == 0);

	return 0;
}}

int main(int argc, char **argv)
{{
	struct bq27xxx_device_info di;
	struct device dev = {{ 0 }};
	struct power_supply_desc desc = {{
		.get_property = bq27xxx_battery_get_property,
	}};
	struct power_supply bat = {{ .desc = &desc }};

	active_di = &di;
	di.bat = &bat;

	if (argc != 2) {{
		fprintf(stderr, "usage: %s setter-expiry|lifecycle\n", argv[0]);
		return 2;
	}}
	if (strcmp(argv[1], "setter-expiry") == 0)
		return run_setter_expiry();
	if (strcmp(argv[1], "lifecycle") == 0)
		return run_lifecycle(&dev);
	fprintf(stderr, "unknown scenario: %s\n", argv[1]);
	return 2;
}}
"""


class Bq27xxxRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._temporary.cleanup)
        directory = Path(cls._temporary.name)
        source = directory / "bq27xxx_runtime_test.c"
        source.write_text(_harness())
        cls.executable = directory / "bq27xxx_runtime_test"

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

    def _run_scenario(self, scenario: str) -> None:
        if self.runner_prefix:
            command = (
                f"{shlex.quote(_wsl_path(self.executable))} "
                f"{shlex.quote(scenario)}"
            )
            result = subprocess.run(
                [*self.runner_prefix, command],
                check=False,
                capture_output=True,
                text=True,
            )
        else:
            result = subprocess.run(
                [str(self.executable), scenario],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_actual_setter_and_expiry_state_machine(self) -> None:
        self._run_scenario("setter-expiry")

    def test_actual_suspend_teardown_resume_lifecycle(self) -> None:
        self._run_scenario("lifecycle")


if __name__ == "__main__":
    unittest.main()
