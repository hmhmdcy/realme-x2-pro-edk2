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
    getter = _extract_function(
        source,
        "static int bq27xxx_battery_get_property(struct power_supply *psy,",
    )
    return rf"""
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#include "bq27xxx-status-policy.h"

#define EXPORT_SYMBOL_GPL(symbol)
#define HZ 100
#define BQ27XXX_MANUFACTURER "test-bq"
#define time_is_before_jiffies(a) false

typedef uint32_t u32;
typedef uint8_t u8;

enum power_supply_property {{
	POWER_SUPPLY_PROP_PRESENT = 0,
	POWER_SUPPLY_PROP_STATUS,
	POWER_SUPPLY_PROP_VOLTAGE_NOW,
	POWER_SUPPLY_PROP_CURRENT_NOW,
	POWER_SUPPLY_PROP_CURRENT_AVG,
	POWER_SUPPLY_PROP_CAPACITY,
	POWER_SUPPLY_PROP_CAPACITY_LEVEL,
	POWER_SUPPLY_PROP_TEMP,
	POWER_SUPPLY_PROP_TIME_TO_EMPTY_NOW,
	POWER_SUPPLY_PROP_TIME_TO_EMPTY_AVG,
	POWER_SUPPLY_PROP_TIME_TO_FULL_NOW,
	POWER_SUPPLY_PROP_TECHNOLOGY,
	POWER_SUPPLY_PROP_CHARGE_NOW,
	POWER_SUPPLY_PROP_CHARGE_FULL,
	POWER_SUPPLY_PROP_CHARGE_FULL_DESIGN,
	POWER_SUPPLY_PROP_ENERGY_FULL_DESIGN,
	POWER_SUPPLY_PROP_VOLTAGE_MIN_DESIGN,
	POWER_SUPPLY_PROP_VOLTAGE_MAX_DESIGN,
	POWER_SUPPLY_PROP_CYCLE_COUNT,
	POWER_SUPPLY_PROP_ENERGY_NOW,
	POWER_SUPPLY_PROP_POWER_AVG,
	POWER_SUPPLY_PROP_HEALTH,
	POWER_SUPPLY_PROP_MANUFACTURER,
}};

enum {{
	POWER_SUPPLY_STATUS_UNKNOWN = 0,
	POWER_SUPPLY_STATUS_CHARGING,
	POWER_SUPPLY_STATUS_DISCHARGING,
	POWER_SUPPLY_STATUS_NOT_CHARGING,
	POWER_SUPPLY_STATUS_FULL,
	POWER_SUPPLY_TECHNOLOGY_UNKNOWN,
	POWER_SUPPLY_TECHNOLOGY_LION,
}};

union power_supply_propval {{
	int intval;
	const char *strval;
}};

struct mutex {{ int unused; }};
struct work_struct {{ int unused; }};
struct delayed_work {{ struct work_struct work; }};
struct power_supply;

struct power_supply_desc {{
	int (*get_property)(struct power_supply *psy,
			    enum power_supply_property psp,
			    union power_supply_propval *val);
}};

struct power_supply {{
	struct power_supply_desc *desc;
}};

struct bq27xxx_reg_cache {{
	int flags;
	int capacity;
}};

struct bq27xxx_device_info {{
	bool removed;
	bool suspended;
	unsigned long last_update;
	union power_supply_propval last_status;
	struct delayed_work full_status_work;
	struct power_supply *bat;
	struct mutex lock;
	struct bq27xxx_reg_cache cache;
	u32 opts;
	u8 *regs;
	unsigned long full_status_deadline;
	u32 full_status_generation;
	bool full_status_override;
}};

#define BQ27XXX_O_MUL_CHEM 1
#define BQ27XXX_REG_TTE 0
#define BQ27XXX_REG_TTECP 0
#define BQ27XXX_REG_TTF 0
#define BQ27XXX_REG_NAC 0
#define INVALID_REG_ADDR 0xff
#define bq27xxx_simple_value(...) 0
#define bq27xxx_battery_capacity_level(...) 0
#define bq27xxx_battery_read_temperature(...) 0
#define bq27xxx_battery_read_time(...) 0
#define bq27xxx_battery_read_nac(...) 0
#define bq27xxx_battery_read_rc(...) 0
#define bq27xxx_battery_read_fcc(...) 0
#define bq27xxx_battery_read_dcap(...) 0
#define bq27xxx_battery_read_dmin_volt(...) 0
#define bq27xxx_battery_read_dmax_volt(...) 0
#define bq27xxx_battery_read_cyct(...) 0
#define bq27xxx_battery_read_energy(...) 0
#define bq27xxx_battery_pwr_avg(...) 0
#define bq27xxx_battery_read_health(...) 0

static unsigned long jiffies = 1000;
static struct bq27xxx_device_info *active_di;
static int lock_depth;
static int raw_calls;
static int raw_values[4];
static int raw_results[4];
static bool revoke_on_first;

static void *power_supply_get_drvdata(struct power_supply *psy)
{{
	(void)psy;
	return active_di;
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

static void bq27xxx_battery_update_unlocked(struct bq27xxx_device_info *di)
{{
	(void)di;
}}

static int bq27xxx_battery_current_and_status(
	struct bq27xxx_device_info *di,
	union power_supply_propval *val_curr,
	union power_supply_propval *val_status,
	void *cache)
{{
	int index = raw_calls++;
	int result = index < 4 ? raw_results[index] : -EIO;
	int value = index < 4 ? raw_values[index] : 0;

	(void)di;
	(void)cache;
	if (val_curr)
		val_curr->intval = 0;
	if (val_status)
		val_status->intval = value;
	if (index == 0 && revoke_on_first) {{
		active_di->full_status_override = false;
		active_di->full_status_deadline = 0;
		active_di->full_status_generation++;
	}}
	return result;
}}

static int bq27xxx_battery_voltage(struct bq27xxx_device_info *di,
				   union power_supply_propval *val)
{{
	(void)di;
	val->intval = 0;
	return 0;
}}

static int bq27xxx_samurai_average_current(
	struct bq27xxx_device_info *di,
	union power_supply_propval *val)
{{
	(void)di;
	val->intval = 0;
	return 0;
}}

{getter}

#define CHECK(condition) do {{ \
	if (!(condition)) {{ \
		fprintf(stderr, "%s:%d: check failed: %s\n", \
			__FILE__, __LINE__, #condition); \
		return 1; \
	}} \
}} while (0)

static void reset_state(struct bq27xxx_device_info *di,
			struct power_supply *bat)
{{
	memset(di, 0, sizeof(*di));
	di->bat = bat;
	di->last_update = jiffies;
	di->full_status_override = true;
	di->full_status_deadline = jiffies + 4;
	di->full_status_generation = 7;
	di->cache.flags = 0;
	active_di = di;
	lock_depth = 0;
	raw_calls = 0;
	memset(raw_values, 0, sizeof(raw_values));
	memset(raw_results, 0, sizeof(raw_results));
	revoke_on_first = false;
}}

int main(void)
{{
	struct bq27xxx_device_info di;
	struct power_supply_desc desc = {{0}};
	struct power_supply bat = {{ .desc = &desc }};
	union power_supply_propval value;

	reset_state(&di, &bat);
	raw_values[0] = POWER_SUPPLY_STATUS_DISCHARGING;
	raw_values[1] = POWER_SUPPLY_STATUS_CHARGING;
	CHECK(bq27xxx_battery_get_property(&bat, POWER_SUPPLY_PROP_STATUS,
					   &value) == 0);
	CHECK(value.intval == POWER_SUPPLY_STATUS_CHARGING);
	CHECK(raw_calls == 2 && lock_depth == 0);

	reset_state(&di, &bat);
	raw_values[0] = POWER_SUPPLY_STATUS_DISCHARGING;
	raw_values[1] = POWER_SUPPLY_STATUS_DISCHARGING;
	CHECK(bq27xxx_battery_get_property(&bat, POWER_SUPPLY_PROP_STATUS,
					   &value) == 0);
	CHECK(value.intval == POWER_SUPPLY_STATUS_FULL);
	CHECK(raw_calls == 2 && lock_depth == 0);

	reset_state(&di, &bat);
	raw_values[0] = POWER_SUPPLY_STATUS_CHARGING;
	CHECK(bq27xxx_battery_get_property(&bat, POWER_SUPPLY_PROP_STATUS,
					   &value) == 0);
	CHECK(value.intval == POWER_SUPPLY_STATUS_CHARGING);
	CHECK(raw_calls == 1 && lock_depth == 0);

	reset_state(&di, &bat);
	raw_values[0] = POWER_SUPPLY_STATUS_DISCHARGING;
	revoke_on_first = true;
	CHECK(bq27xxx_battery_get_property(&bat, POWER_SUPPLY_PROP_STATUS,
					   &value) == 0);
	CHECK(value.intval == POWER_SUPPLY_STATUS_DISCHARGING);
	CHECK(raw_calls == 1 && lock_depth == 0);

	reset_state(&di, &bat);
	raw_values[0] = POWER_SUPPLY_STATUS_DISCHARGING;
	raw_results[1] = -EIO;
	CHECK(bq27xxx_battery_get_property(&bat, POWER_SUPPLY_PROP_STATUS,
					   &value) == -EIO);
	CHECK(raw_calls == 2 && lock_depth == 0);

	reset_state(&di, &bat);
	di.cache.flags = -ENODEV;
	CHECK(bq27xxx_battery_get_property(&bat, POWER_SUPPLY_PROP_STATUS,
					   &value) == -ENODEV);
	CHECK(raw_calls == 0 && lock_depth == 0);

	return 0;
}}
"""


class Bq27xxxGetterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._temporary.cleanup)
        directory = Path(cls._temporary.name)
        source = directory / "bq27xxx_getter_test.c"
        source.write_text(_harness())
        cls.executable = directory / "bq27xxx_getter_test"

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

    def test_actual_getter_rechecks_raw_status_and_generation(self) -> None:
        if self.runner_prefix:
            result = subprocess.run(
                [*self.runner_prefix, shlex.quote(_wsl_path(self.executable))],
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
