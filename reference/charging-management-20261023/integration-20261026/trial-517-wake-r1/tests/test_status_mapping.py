from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


SOURCE_ROOT = (
    Path(__file__).resolve().parents[4]
    / "charging-session-20261023"
    / "r8-source-integration"
    / "kernel-sources"
    / "drivers"
    / "power"
    / "supply"
)
HEADER = SOURCE_ROOT / "samurai-status.h"
DRIVER = SOURCE_ROOT / "samurai-mp2650.c"
BQ_PATCH = SOURCE_ROOT / "bq27xxx-status-override.patch"
BQ_POLICY = SOURCE_ROOT / "bq27xxx-status-policy.h"


C_HARNESS = r"""
#include <stdio.h>
#include <string.h>
#include <limits.h>

#include "samurai-status.h"
#include "bq27xxx-status-policy.h"

#define CHECK(condition) do { \
	if (!(condition)) { \
		fprintf(stderr, "%s:%d: check failed: %s\n", \
			__FILE__, __LINE__, #condition); \
		return 1; \
	} \
} while (0)

static struct sm_full_status_evidence valid_evidence(void)
{
	return (struct sm_full_status_evidence){
		.control = 1,
		.auto_requested = 1,
		.online = 1,
		.sample_valid = 1,
		.protection_ok = 1,
		.logical_full = 1,
		.hold_requested = 1,
		.full_holding = 1,
	};
}

static int required_evidence(const char *name)
{
	struct sm_full_status_evidence e;

#define REQUIRE_TRUE(field, label) do { \
	e = valid_evidence(); \
	e.field = 0; \
	if (sm_full_status_evidence_valid(&e)) { \
		fprintf(stderr, "%s accepted without %s\n", name, label); \
		return 1; \
	} \
} while (0)
#define REQUIRE_FALSE(field, label) do { \
	e = valid_evidence(); \
	e.field = 1; \
	if (sm_full_status_evidence_valid(&e)) { \
		fprintf(stderr, "%s accepted with %s\n", name, label); \
		return 1; \
	} \
} while (0)

	REQUIRE_TRUE(control, "control");
	REQUIRE_TRUE(auto_requested, "AUTO");
	REQUIRE_TRUE(online, "online source");
	REQUIRE_TRUE(sample_valid, "fresh sample");
	REQUIRE_TRUE(protection_ok, "protection");
	REQUIRE_TRUE(logical_full, "logical Full");
	REQUIRE_TRUE(hold_requested, "hold request");
	REQUIRE_TRUE(full_holding, "confirmed hold");
	REQUIRE_FALSE(cycle_timeout, "timeout");
	REQUIRE_FALSE(latched, "latch");
	REQUIRE_FALSE(last_error, "error");
	REQUIRE_FALSE(stop_error, "stop error");
	REQUIRE_FALSE(source_inhibit, "source inhibit");
	REQUIRE_FALSE(gauge_charge_stop, "gauge charge stop");
	return 0;
}

static int base_safety(const char *name)
{
	struct sm_full_status_evidence e;

#define REQUIRE_BASE_TRUE(field, label) do { \
	e = valid_evidence(); \
	e.field = 1; \
	if (!sm_full_status_safety_valid(&e)) { \
		fprintf(stderr, "%s rejected with %s\n", name, label); \
		return 1; \
	} \
} while (0)
#define REQUIRE_BASE_FALSE(field, label) do { \
	e = valid_evidence(); \
	e.field = 0; \
	if (sm_full_status_safety_valid(&e)) { \
		fprintf(stderr, "%s accepted without %s\n", name, label); \
		return 1; \
	} \
} while (0)
#define REQUIRE_BASE_UNSAFE(field, label) do { \
	e = valid_evidence(); \
	e.field = 1; \
	if (sm_full_status_safety_valid(&e)) { \
		fprintf(stderr, "%s accepted with %s\n", name, label); \
		return 1; \
	} \
} while (0)

	REQUIRE_BASE_TRUE(control, "control");
	REQUIRE_BASE_TRUE(logical_full, "logical Full");
	REQUIRE_BASE_TRUE(hold_requested, "hold request");
	REQUIRE_BASE_TRUE(full_holding, "confirmed hold");
	REQUIRE_BASE_FALSE(auto_requested, "AUTO");
	REQUIRE_BASE_FALSE(online, "online source");
	REQUIRE_BASE_FALSE(sample_valid, "fresh sample");
	REQUIRE_BASE_FALSE(protection_ok, "protection");
	REQUIRE_BASE_UNSAFE(cycle_timeout, "timeout");
	REQUIRE_BASE_UNSAFE(latched, "latch");
	REQUIRE_BASE_UNSAFE(last_error, "error");
	REQUIRE_BASE_UNSAFE(stop_error, "stop error");
	REQUIRE_BASE_UNSAFE(source_inhibit, "source inhibit");
	REQUIRE_BASE_UNSAFE(gauge_charge_stop, "gauge charge stop");

	e = valid_evidence();
	e.control = 0;
	e.logical_full = 0;
	e.hold_requested = 0;
	e.full_holding = 0;
	CHECK(sm_reg13_full(0x0e, &e));
	return 0;
}

static int bq_policy(const char *name)
{
	(void)name;
	CHECK(BQ27XXX_FULL_STATUS_TTL_MS == 4000);
	CHECK(bq27xxx_full_status_active(1, 100, 99));
	CHECK(!bq27xxx_full_status_active(1, 100, 100));
	CHECK(!bq27xxx_full_status_active(1, 100, 101));
	CHECK(!bq27xxx_full_status_active(0, 100, 99));
	CHECK(bq27xxx_full_status_active(1, 0, ULONG_MAX));
	CHECK(bq27xxx_full_status_confirmed(1, 100, 99, 7, 7));
	CHECK(!bq27xxx_full_status_confirmed(1, 100, 99, 8, 7));
	CHECK(!bq27xxx_full_status_confirmed(0, 100, 99, 7, 7));
	CHECK(!bq27xxx_full_status_confirmed(1, 100, 100, 7, 7));
	CHECK(!bq27xxx_full_status_changed(1, 100, 99, 1));
	CHECK(bq27xxx_full_status_changed(1, 100, 99, 0));
	CHECK(bq27xxx_full_status_changed(1, 100, 100, 1));
	CHECK(!bq27xxx_full_status_changed(1, 100, 100, 0));
	CHECK(bq27xxx_full_status_changed(0, 100, 99, 1));
	CHECK(!bq27xxx_full_status_changed(0, 100, 99, 0));

	CHECK(bq27xxx_full_status_apply(1, 1, 1, 4) == 1);
	CHECK(bq27xxx_full_status_apply(2, 1, 1, 4) == 4);
	CHECK(bq27xxx_full_status_apply(3, 1, 1, 4) == 4);
	CHECK(bq27xxx_full_status_apply(4, 1, 1, 4) == 4);
	CHECK(bq27xxx_full_status_apply(1, 0, 1, 4) == 1);
	CHECK(bq27xxx_full_status_apply(2, 0, 1, 4) == 2);
	CHECK(bq27xxx_full_status_apply(3, 0, 1, 4) == 3);
	CHECK(bq27xxx_full_status_apply(4, 0, 1, 4) == 4);
	return 0;
}

int main(int argc, char **argv)
{
	struct sm_full_status_evidence e = valid_evidence();

	if (argc != 2)
		return 2;
	if (!strcmp(argv[1], "valid")) {
		CHECK(sm_full_status_evidence_valid(&e));
		CHECK(sm_reg13_full(0x02, &e));
		CHECK(sm_reg13_full(0x0e, &e));
		CHECK(sm_gauge_full_override(0, &e));
		CHECK(!sm_gauge_full_override(1, &e));
		return 0;
	}
	if (!strcmp(argv[1], "required"))
		return required_evidence(argv[1]);
	if (!strcmp(argv[1], "base-safety"))
		return base_safety(argv[1]);
	if (!strcmp(argv[1], "bq-policy"))
		return bq_policy(argv[1]);
	if (!strcmp(argv[1], "raw-wins")) {
		CHECK(!sm_reg13_full(0x06, &e));
		CHECK(!sm_reg13_full(0x0a, &e));
		CHECK(!sm_reg13_full(0x00, &e));
		CHECK(!sm_gauge_full_override(1, &e));
		return 0;
	}
	if (!strcmp(argv[1], "hardware-full")) {
		e.logical_full = 0;
		e.hold_requested = 0;
		e.full_holding = 0;
		CHECK(sm_reg13_full(0x0e, &e));
		CHECK(!sm_reg13_full(0x02, NULL));
		return 0;
	}
	if (!strcmp(argv[1], "hardware-requires-safety")) {
		e.online = 0;
		CHECK(!sm_reg13_full(0x0e, &e));
		e = valid_evidence();
		e.protection_ok = 0;
		CHECK(!sm_reg13_full(0x0e, &e));
		e = valid_evidence();
		e.latched = 1;
		CHECK(!sm_reg13_full(0x0e, &e));
		e = valid_evidence();
		e.cycle_timeout = 1;
		CHECK(!sm_reg13_full(0x0e, &e));
		return 0;
	}
	return 2;
}
"""


def _wsl_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    return f"/mnt/{drive}/{resolved.as_posix().split(':', 1)[1].lstrip('/')}"


class StatusMappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._temporary.cleanup)
        directory = Path(cls._temporary.name)
        source = directory / "status_mapping_test.c"
        source.write_text(C_HARNESS)
        cls.executable = directory / "status_mapping_test"

        if os.name == "nt":
            if not shutil.which("wsl.exe"):
                raise unittest.SkipTest("WSL compiler is unavailable")
            header_dir = _wsl_path(SOURCE_ROOT)
            source_arg = _wsl_path(source)
            executable = _wsl_path(cls.executable)
            command = (
                f"cc -std=c11 -Wall -Wextra -Werror -I {shlex.quote(header_dir)} "
                f"{shlex.quote(source_arg)} -o {shlex.quote(executable)}"
            )
            cls.runner_prefix = ["wsl.exe", "-e", "bash", "-lc"]
            cls._run_command([*cls.runner_prefix, command])
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

    @classmethod
    def _run_command(cls, argv: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(argv, check=True, capture_output=True, text=True)

    def _case(self, name: str) -> None:
        if self.runner_prefix:
            command = shlex.quote(_wsl_path(self.executable)) + " " + shlex.quote(name)
            result = subprocess.run(
                [*self.runner_prefix, command],
                check=False,
                capture_output=True,
                text=True,
            )
        else:
            result = subprocess.run(
                [str(self.executable), name],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_validated_normal_hold_maps_to_full(self) -> None:
        self._case("valid")

    def test_every_safety_and_lifecycle_field_is_required(self) -> None:
        self._case("required")

    def test_base_safety_is_separate_from_software_hold(self) -> None:
        self._case("base-safety")

    def test_bq_policy_lease_and_raw_precedence(self) -> None:
        self._case("bq-policy")

    def test_raw_charging_and_detach_are_never_masked(self) -> None:
        self._case("raw-wins")

    def test_hardware_full_does_not_depend_on_software_hold(self) -> None:
        self._case("hardware-full")

    def test_hardware_full_still_requires_safety_evidence(self) -> None:
        self._case("hardware-requires-safety")

    def test_driver_uses_the_shared_policy_for_both_supplies(self) -> None:
        source = DRIVER.read_text()
        self.assertIn("sm_reg13_full(value, &evidence)", source)
        self.assertIn("sm_gauge_full_override(false, &e)", source)
        self.assertIn("bq27xxx_battery_set_status_override", source)
        self.assertIn("c->full_holding = false;", source)
        self.assertIn("c->hold_requested = false;", source)

    def test_gauge_patch_preserves_raw_charging_precedence(self) -> None:
        patch = BQ_PATCH.read_text()
        self.assertIn("full_status_override", patch)
        self.assertIn("bq27xxx_full_status_active", patch)
        self.assertIn("bq27xxx_full_status_confirmed", patch)
        self.assertIn("bq27xxx_full_status_changed", patch)
        self.assertIn("bq27xxx_full_status_apply", patch)
        self.assertIn("POWER_SUPPLY_STATUS_CHARGING", patch)
        self.assertIn("bq27xxx_samurai_instant(di)", patch)
        self.assertIn("BQ27XXX_FULL_STATUS_TTL_MS", patch)
        self.assertIn("full_status_deadline", patch)
        self.assertIn("bq27xxx_full_status_expire", patch)
        self.assertIn("EXPORT_SYMBOL_GPL(bq27xxx_battery_set_status_override)", patch)

    def test_bridge_is_explicitly_an_image_level_dependency(self) -> None:
        driver = DRIVER.read_text()
        patch = BQ_PATCH.read_text()
        self.assertIn('#error "samurai Full-status bridge requires', driver)
        self.assertIn("!IS_REACHABLE(CONFIG_BATTERY_BQ27XXX)", driver)
        self.assertIn("not\n * deployable as a module-only update", driver)
        self.assertIn("EXPORT_SYMBOL_GPL(bq27xxx_battery_set_status_override)", patch)
        self.assertIn("int bq27xxx_battery_set_status_override", patch)
        self.assertTrue(BQ_POLICY.is_file())

    def test_source_notifier_clears_full_before_deferred_poll(self) -> None:
        source = DRIVER.read_text()
        notifier = source.split("static int sm_supply_changed", 1)[1].split(
            "static int sm_adc", 1
        )[0]
        self.assertIn("mutex_lock(&c->lock);", notifier)
        self.assertIn("sm_clear_full_status_locked(c);", notifier)
        self.assertLess(
            notifier.index("sm_clear_full_status_locked(c);"),
            notifier.index("mod_delayed_work(system_wq, &c->work, 0);"),
        )


if __name__ == "__main__":
    unittest.main()
