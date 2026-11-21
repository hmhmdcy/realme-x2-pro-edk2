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


C_HARNESS = r"""
#include <errno.h>
#include <stdio.h>
#include <string.h>

#include "mp2650-core.h"

#define CHECK(condition) do { \
	if (!(condition)) { \
		fprintf(stderr, "%s:%d: check failed: %s\n", \
			__FILE__, __LINE__, #condition); \
		return 1; \
	} \
} while (0)

struct fake {
	int reg[256];
	int writes[256];
	int fail_write_reg;
	int fail_enable_write;
	int corrupt_read_reg;
	int corrupt_read_value;
	int unsafe_config_write;
};

static int fake_read(void *ctx, unsigned int reg)
{
	struct fake *f = ctx;

	if (reg >= 256)
		return -EINVAL;
	if ((int)reg == f->corrupt_read_reg)
		return f->corrupt_read_value;
	return f->reg[reg];
}

static int fake_write(void *ctx, unsigned int reg, unsigned int value)
{
	struct fake *f = ctx;

	if (reg >= 256)
		return -EINVAL;
	if ((reg == 0x00 || reg == 0x0f || reg == 0x02 ||
	     reg == 0x03 || reg == 0x04 || reg == 0x07) &&
	    (f->reg[0x08] & 0x10))
		f->unsafe_config_write = 1;
	f->writes[reg]++;
	if ((int)reg == f->fail_write_reg)
		return -EIO;
	if ((int)reg == 0x08 && (value & 0x10) && f->fail_enable_write)
		return -EIO;
	f->reg[reg] = value;
	return 0;
}

static void configure(struct fake *f, int reg07, int reg03, int control)
{
	memset(f, 0, sizeof(*f));
	f->fail_write_reg = -1;
	f->fail_enable_write = 0;
	f->corrupt_read_reg = -1;
	f->reg[0x00] = 0x0a;
	f->reg[0x0f] = 0x0a;
	f->reg[0x02] = 0x05;
	f->reg[0x03] = reg03;
	f->reg[0x04] = 0x6e;
	f->reg[0x05] = 0x00;
	f->reg[0x07] = reg07;
	f->reg[0x08] = control;
	f->reg[0x09] = 0x48;
}

static struct sm_target target(void)
{
	return (struct sm_target){
		.enable = 1,
		.input_ua = 500000,
		.current_ua = 250000,
		.cell_uv = 4400000,
	};
}

static int normalize_case(void)
{
	struct fake f;
	struct sm_io io;
	struct sm_target t = target();
	int stop_error;

	configure(&f, 0x14, 0x31, 0x16);
	io = (struct sm_io){ .ctx = &f, .read = fake_read, .write = fake_write };
	CHECK(sm_apply(&io, &t, &stop_error) == 0);
	CHECK(stop_error == 0);
	CHECK(f.reg[0x07] == 0x04);
	CHECK(f.writes[0x07] == 1);
	CHECK(f.reg[0x03] == 0x91);
	CHECK(f.writes[0x03] == 1);
	CHECK(!f.unsafe_config_write);
	CHECK((f.reg[0x08] & 0x18) == 0x10);
	return 0;
}

static int already_normalized_case(void)
{
	struct fake f;
	struct sm_io io;
	struct sm_target t = target();
	int stop_error;

	configure(&f, 0x04, 0x91, 0x16);
	io = (struct sm_io){ .ctx = &f, .read = fake_read, .write = fake_write };
	CHECK(sm_apply(&io, &t, &stop_error) == 0);
	CHECK(stop_error == 0);
	for (int i = 0; i < 256; i++)
		CHECK(f.writes[i] == 0);
	return 0;
}

static int preserve_otg_case(void)
{
	struct fake f;
	struct sm_io io;
	struct sm_target t = target();
	int stop_error;

	configure(&f, 0x1f, 0x39, 0x16);
	io = (struct sm_io){ .ctx = &f, .read = fake_read, .write = fake_write };
	CHECK(sm_apply(&io, &t, &stop_error) == 0);
	CHECK(f.reg[0x07] == 0x0f);
	CHECK(f.reg[0x03] == 0x91);
	CHECK(!f.unsafe_config_write);
	return 0;
}

static int clear_high_threshold_case(void)
{
	struct fake f;
	struct sm_io io;
	struct sm_target t = target();
	int stop_error;

	configure(&f, 0x30, 0x31, 0x16);
	io = (struct sm_io){ .ctx = &f, .read = fake_read, .write = fake_write };
	CHECK(sm_apply(&io, &t, &stop_error) == 0);
	CHECK(f.reg[0x07] == 0x00);
	CHECK(!f.unsafe_config_write);
	return 0;
}

static int invalid_cell_count_case(void)
{
	struct fake f;
	struct sm_io io;
	struct sm_target t = target();
	int stop_error;

	configure(&f, 0xc4, 0x91, 0x16);
	io = (struct sm_io){ .ctx = &f, .read = fake_read, .write = fake_write };
	CHECK(sm_apply(&io, &t, &stop_error) == -EOPNOTSUPP);
	CHECK(stop_error == 0);
	CHECK((f.reg[0x08] & 0x18) == 0x08);
	return 0;
}

static int write_failure_case(void)
{
	struct fake f;
	struct sm_io io;
	struct sm_target t = target();
	int stop_error;

	configure(&f, 0x14, 0x91, 0x16);
	f.fail_write_reg = 0x07;
	io = (struct sm_io){ .ctx = &f, .read = fake_read, .write = fake_write };
	CHECK(sm_apply(&io, &t, &stop_error) == -EIO);
	CHECK(stop_error == 0);
	CHECK(!f.unsafe_config_write);
	CHECK((f.reg[0x08] & 0x18) == 0x08);
	return 0;
}

static int readback_failure_case(void)
{
	struct fake f;
	struct sm_io io;
	struct sm_target t = target();
	int stop_error;

	configure(&f, 0x04, 0x91, 0x16);
	f.reg[0x03] = 0x31;
	f.corrupt_read_reg = 0x03;
	f.corrupt_read_value = 0x90;
	io = (struct sm_io){ .ctx = &f, .read = fake_read, .write = fake_write };
	CHECK(sm_apply(&io, &t, &stop_error) == -EIO);
	CHECK(stop_error == 0);
	CHECK(!f.unsafe_config_write);
	CHECK((f.reg[0x08] & 0x18) == 0x08);
	return 0;
}

static int config_failure_matrix_case(void)
{
	const int failed_regs[] = { 0x0f, 0x00, 0x02, 0x03, 0x04 };

	for (unsigned int i = 0; i < sizeof(failed_regs) / sizeof(failed_regs[0]); i++) {
		struct fake f;
		struct sm_io io;
		struct sm_target t = target();
		int stop_error;

		configure(&f, 0x14, 0x31, 0x16);
		f.reg[0x00] = 0x01;
		f.reg[0x0f] = 0x02;
		f.reg[0x02] = 0x03;
		f.reg[0x04] = 0x01;
		f.fail_write_reg = failed_regs[i];
		io = (struct sm_io){ .ctx = &f, .read = fake_read, .write = fake_write };
		CHECK(sm_apply(&io, &t, &stop_error) == -EIO);
		CHECK(stop_error == 0);
		CHECK(!f.unsafe_config_write);
		CHECK((f.reg[0x08] & 0x18) == 0x08);
	}
	return 0;
}

static int enable_failure_case(void)
{
	struct fake f;
	struct sm_io io;
	struct sm_target t = target();
	int stop_error;

	configure(&f, 0x04, 0x91, 0x06);
	f.fail_enable_write = 1;
	io = (struct sm_io){ .ctx = &f, .read = fake_read, .write = fake_write };
	CHECK(sm_apply(&io, &t, &stop_error) == -EIO);
	CHECK(stop_error == 0);
	CHECK(!f.unsafe_config_write);
	CHECK((f.reg[0x08] & 0x18) == 0x08);
	CHECK(f.writes[0x08] == 2);
	return 0;
}

static int full_hold_normalize_case(void)
{
	struct fake f;
	struct sm_io io;
	struct sm_target t = target();
	int stop_error;

	configure(&f, 0x24, 0x90, 0x06);
	io = (struct sm_io){ .ctx = &f, .read = fake_read, .write = fake_write };
	CHECK(sm_apply_charge_hold(&io, &t, &stop_error) == 0);
	CHECK(stop_error == 0);
	CHECK(f.reg[0x07] == 0x04);
	CHECK(f.reg[0x03] == 0x91);
	CHECK((f.reg[0x08] & 0x18) == 0);
	return 0;
}

static int full_hold_failure_case(void)
{
	struct fake f;
	struct sm_io io;
	struct sm_target t = target();
	int stop_error;

	configure(&f, 0x14, 0x31, 0x06);
	f.fail_write_reg = 0x07;
	io = (struct sm_io){ .ctx = &f, .read = fake_read, .write = fake_write };
	CHECK(sm_apply_charge_hold(&io, &t, &stop_error) == -EIO);
	CHECK(stop_error == 0);
	CHECK(!f.unsafe_config_write);
	CHECK((f.reg[0x08] & 0x18) == 0x08);
	return 0;
}

int main(int argc, char **argv)
{
	if (argc != 2)
		return 2;
	if (!strcmp(argv[1], "normalize"))
		return normalize_case();
	if (!strcmp(argv[1], "already-normalized"))
		return already_normalized_case();
	if (!strcmp(argv[1], "preserve-otg"))
		return preserve_otg_case();
	if (!strcmp(argv[1], "clear-high-threshold"))
		return clear_high_threshold_case();
	if (!strcmp(argv[1], "invalid-cell-count"))
		return invalid_cell_count_case();
	if (!strcmp(argv[1], "write-failure"))
		return write_failure_case();
	if (!strcmp(argv[1], "readback-failure"))
		return readback_failure_case();
	if (!strcmp(argv[1], "config-failure-matrix"))
		return config_failure_matrix_case();
	if (!strcmp(argv[1], "enable-failure"))
		return enable_failure_case();
	if (!strcmp(argv[1], "full-hold-normalize"))
		return full_hold_normalize_case();
	if (!strcmp(argv[1], "full-hold-failure"))
		return full_hold_failure_case();
	return 2;
}
"""


def _wsl_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    return f"/mnt/{drive}/{resolved.as_posix().split(':', 1)[1].lstrip('/')}"


class PrechargeMappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._temporary.cleanup)
        directory = Path(cls._temporary.name)
        source = directory / "precharge_mapping_test.c"
        source.write_text(C_HARNESS)
        cls.executable = directory / "precharge_mapping_test"

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

    def test_normalizes_6600mv_threshold_and_480ma_precharge(self) -> None:
        self._case("normalize")

    def test_already_normalized_configuration_is_not_rewritten(self) -> None:
        self._case("already-normalized")

    def test_threshold_update_preserves_otg_bits(self) -> None:
        self._case("preserve-otg")

    def test_high_threshold_bits_are_cleared(self) -> None:
        self._case("clear-high-threshold")

    def test_invalid_cell_count_never_enables_charge(self) -> None:
        self._case("invalid-cell-count")

    def test_write_failure_stops_without_enabling_charge(self) -> None:
        self._case("write-failure")

    def test_disagreeing_readback_stops_without_enabling_charge(self) -> None:
        self._case("readback-failure")

    def test_all_config_writes_fail_closed_after_stop(self) -> None:
        self._case("config-failure-matrix")

    def test_final_enable_failure_is_never_reported_as_success(self) -> None:
        self._case("enable-failure")

    def test_full_hold_uses_the_same_safe_register_defaults(self) -> None:
        self._case("full-hold-normalize")

    def test_full_hold_failure_stops_without_enabling_charge(self) -> None:
        self._case("full-hold-failure")


if __name__ == "__main__":
    unittest.main()
