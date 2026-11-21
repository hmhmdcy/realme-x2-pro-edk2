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
	struct {
		unsigned int reg;
		unsigned int value;
		int result;
	} trace[512];
	int trace_len;
	int fail_write_reg;
	int fail_enable_write;
	int fail_hold_clear_write;
	int fail_unpause_write;
	int corrupt_read_reg;
	int corrupt_read_value;
	int corrupt_readback_reg;
	int corrupt_readback_value;
	int corrupt_readback_pending;
	int unsafe_config_write;
};

static int fake_read(void *ctx, unsigned int reg)
{
	struct fake *f = ctx;

	if (reg >= 256)
		return -EINVAL;
	if ((int)reg == f->corrupt_read_reg)
		return f->corrupt_read_value;
	if (f->corrupt_readback_pending &&
	    (int)reg == f->corrupt_readback_reg) {
		f->corrupt_readback_pending = 0;
		return f->corrupt_readback_value;
	}
	return f->reg[reg];
}

static int fake_write(void *ctx, unsigned int reg, unsigned int value)
{
	struct fake *f = ctx;

	if (reg >= 256)
		return -EINVAL;
	if (f->trace_len >= (int)(sizeof(f->trace) / sizeof(f->trace[0])))
		return -EOVERFLOW;
	if ((reg == 0x00 || reg == 0x0f || reg == 0x02 ||
	     reg == 0x03 || reg == 0x04 || reg == 0x07) &&
	    (f->reg[0x08] & 0x10))
		f->unsafe_config_write = 1;
	f->writes[reg]++;
	f->trace[f->trace_len].reg = reg;
	f->trace[f->trace_len].value = value;
	f->trace[f->trace_len].result = 0;
	if ((int)reg == f->fail_write_reg ||
	    (reg == 0x08 && value == 0x06 && f->fail_hold_clear_write &&
	     f->reg[0x08] == 0x16) ||
	    (reg == 0x08 && value == 0x06 && f->fail_unpause_write &&
	     f->reg[0x08] == 0x0e)) {
		f->trace[f->trace_len].result = -EIO;
		f->trace_len++;
		return -EIO;
	}
	if ((int)reg == 0x08 && (value & 0x10) && f->fail_enable_write) {
		f->trace[f->trace_len].result = -EIO;
		f->trace_len++;
		return -EIO;
	}
	f->trace_len++;
	f->reg[reg] = value;
	if ((int)reg == f->corrupt_readback_reg)
		f->corrupt_readback_pending = 1;
	return 0;
}

static int expect_write(const struct fake *f, int index,
			unsigned int reg, unsigned int value)
{
	if (index >= f->trace_len) {
		fprintf(stderr, "missing write %d: %02x=%02x\n", index, reg, value);
		return 1;
	}
	if (f->trace[index].reg != reg || f->trace[index].value != value) {
		fprintf(stderr, "write %d: got %02x=%02x, expected %02x=%02x\n",
			index, f->trace[index].reg, f->trace[index].value,
			reg, value);
		return 1;
	}
	return 0;
}

static int expect_clean_trace(const struct fake *f,
			      const unsigned int *regs,
			      const unsigned int *values, int count)
{
	int i;

	if (f->trace_len != count) {
		fprintf(stderr, "trace length: got %d, expected %d\n",
			f->trace_len, count);
		return 1;
	}
	for (i = 0; i < count; i++) {
		if (expect_write(f, i, regs[i], values[i]))
			return 1;
		if (f->trace[i].result) {
			fprintf(stderr, "write %d failed unexpectedly: %d\n",
				i, f->trace[i].result);
			return 1;
		}
	}
	return 0;
}

static void configure(struct fake *f, int reg07, int reg03, int control)
{
	memset(f, 0, sizeof(*f));
	f->fail_write_reg = -1;
	f->fail_enable_write = 0;
	f->fail_hold_clear_write = 0;
	f->fail_unpause_write = 0;
	f->corrupt_read_reg = -1;
	f->corrupt_readback_reg = -1;
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
	f.reg[0x00] = 0x01;
	f.reg[0x0f] = 0x02;
	f.reg[0x02] = 0x03;
	f.reg[0x04] = 0x01;
	io = (struct sm_io){ .ctx = &f, .read = fake_read, .write = fake_write };
	CHECK(sm_apply(&io, &t, &stop_error) == 0);
	CHECK(stop_error == 0);
	CHECK(f.reg[0x07] == 0x04);
	CHECK(f.writes[0x07] == 1);
	CHECK(f.reg[0x03] == 0x91);
	CHECK(f.writes[0x03] == 1);
	CHECK(!f.unsafe_config_write);
	CHECK((f.reg[0x08] & 0x18) == 0x10);
	CHECK(f.trace_len == 8);
	CHECK(!expect_write(&f, 0, 0x08, 0x0e));
	CHECK(!expect_write(&f, 1, 0x07, 0x04));
	CHECK(!expect_write(&f, 2, 0x0f, 0x0a));
	CHECK(!expect_write(&f, 3, 0x00, 0x0a));
	CHECK(!expect_write(&f, 4, 0x02, 0x05));
	CHECK(!expect_write(&f, 5, 0x03, 0x91));
	CHECK(!expect_write(&f, 6, 0x04, 0x6e));
	CHECK(!expect_write(&f, 7, 0x08, 0x16));
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
	const unsigned int expected_regs[] = {
		0x08, 0x07, 0x0f, 0x00, 0x02, 0x03, 0x04
	};
	const unsigned int expected_values[] = {
		0x0e, 0x04, 0x0a, 0x0a, 0x05, 0x91, 0x6e
	};
	const int failed_write_index[] = { 1, 2, 3, 4, 5, 6 };

	for (unsigned int i = 0;
	     i < sizeof(failed_write_index) / sizeof(failed_write_index[0]);
	     i++) {
		struct fake f;
		struct sm_io io;
		struct sm_target t = target();
		int stop_error;
		int failed_index = failed_write_index[i];

		configure(&f, 0x14, 0x31, 0x16);
		f.reg[0x00] = 0x01;
		f.reg[0x0f] = 0x02;
		f.reg[0x02] = 0x03;
		f.reg[0x04] = 0x01;
		f.fail_write_reg = expected_regs[failed_index];
		io = (struct sm_io){ .ctx = &f, .read = fake_read, .write = fake_write };
		CHECK(sm_apply(&io, &t, &stop_error) == -EIO);
		CHECK(stop_error == 0);
		CHECK(!f.unsafe_config_write);
		CHECK((f.reg[0x08] & 0x18) == 0x08);
		CHECK(f.trace_len == failed_index + 1);
		for (int trace_index = 0; trace_index < failed_index; trace_index++) {
			CHECK(!expect_write(&f, trace_index,
				expected_regs[trace_index],
				expected_values[trace_index]));
			CHECK(f.trace[trace_index].result == 0);
		}
		CHECK(!expect_write(&f, failed_index,
			expected_regs[failed_index], expected_values[failed_index]));
		CHECK(f.trace[failed_index].result == -EIO);
	}
	return 0;
}

static int enable_failure_case(void)
{
	struct fake f;
	struct sm_io io;
	struct sm_target t = target();
	int stop_error;

	configure(&f, 0x14, 0x31, 0x16);
	f.reg[0x00] = 0x01;
	f.reg[0x0f] = 0x02;
	f.reg[0x02] = 0x03;
	f.reg[0x04] = 0x01;
	f.fail_enable_write = 1;
	io = (struct sm_io){ .ctx = &f, .read = fake_read, .write = fake_write };
	CHECK(sm_apply(&io, &t, &stop_error) == -EIO);
	CHECK(stop_error == 0);
	CHECK(!f.unsafe_config_write);
	CHECK((f.reg[0x08] & 0x18) == 0x08);
	CHECK(f.writes[0x08] == 2);
	CHECK(f.trace_len == 8);
	CHECK(!expect_write(&f, 7, 0x08, 0x16));
	CHECK(f.trace[7].result == -EIO);
	return 0;
}

static int full_hold_normalize_case(void)
{
	struct fake f;
	struct sm_io io;
	struct sm_target t = target();
	int stop_error;
	const unsigned int expected_regs[] = {
		0x08, 0x08, 0x07, 0x0f, 0x00, 0x02, 0x03, 0x04, 0x08
	};
	const unsigned int expected_values[] = {
		0x06, 0x0e, 0x04, 0x0a, 0x0a, 0x05, 0x91, 0x6e, 0x06
	};

	configure(&f, 0x24, 0x90, 0x16);
	f.reg[0x00] = 0x01;
	f.reg[0x0f] = 0x02;
	f.reg[0x02] = 0x03;
	f.reg[0x04] = 0x01;
	io = (struct sm_io){ .ctx = &f, .read = fake_read, .write = fake_write };
	CHECK(sm_apply_charge_hold(&io, &t, &stop_error) == 0);
	CHECK(stop_error == 0);
	CHECK(f.reg[0x07] == 0x04);
	CHECK(f.reg[0x03] == 0x91);
	CHECK((f.reg[0x08] & 0x18) == 0);
	CHECK(!expect_clean_trace(&f, expected_regs, expected_values, 9));
	for (int reg = 0; reg < 256; reg++) {
		int expected_count = 0;

		if (reg == 0x08)
			expected_count = 3;
		else if (reg == 0x07 || reg == 0x0f || reg == 0x00 ||
			 reg == 0x02 || reg == 0x03 || reg == 0x04)
			expected_count = 1;
		CHECK(f.writes[reg] == expected_count);
	}
	for (int i = 0; i < f.trace_len; i++)
		CHECK(!(f.trace[i].reg == 0x08 && (f.trace[i].value & 0x10)));
	return 0;
}

static int full_hold_config_write_failure_case(void)
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

static int full_hold_final_unpause_failure_case(void)
{
	struct fake f;
	struct sm_io io;
	struct sm_target t = target();
	int stop_error;

	configure(&f, 0x24, 0x90, 0x16);
	f.reg[0x00] = 0x01;
	f.reg[0x0f] = 0x02;
	f.reg[0x02] = 0x03;
	f.reg[0x04] = 0x01;
	f.fail_unpause_write = 1;
	io = (struct sm_io){ .ctx = &f, .read = fake_read, .write = fake_write };
	CHECK(sm_apply_charge_hold(&io, &t, &stop_error) == -EIO);
	CHECK(stop_error == 0);
	CHECK(!f.unsafe_config_write);
	CHECK((f.reg[0x08] & 0x18) == 0x08);
	CHECK(f.trace_len == 9);
	CHECK(!expect_write(&f, 8, 0x08, 0x06));
	CHECK(f.trace[8].result == -EIO);
	for (int i = 0; i < 8; i++)
		CHECK(f.trace[i].result == 0);
	return 0;
}

static int full_hold_first_stop_failure_case(void)
{
	struct fake f;
	struct sm_io io;
	struct sm_target t = target();
	int stop_error;

	configure(&f, 0x24, 0x90, 0x16);
	f.fail_hold_clear_write = 1;
	io = (struct sm_io){ .ctx = &f, .read = fake_read, .write = fake_write };
	CHECK(sm_apply_charge_hold(&io, &t, &stop_error) == -EIO);
	CHECK(stop_error == 0);
	CHECK(!f.unsafe_config_write);
	CHECK((f.reg[0x08] & 0x18) == 0x08);
	CHECK(f.trace_len == 2);
	CHECK(!expect_write(&f, 0, 0x08, 0x06));
	CHECK(f.trace[0].result == -EIO);
	CHECK(!expect_write(&f, 1, 0x08, 0x0e));
	CHECK(f.trace[1].result == 0);
	for (int reg = 0; reg < 256; reg++)
		if (reg != 0x08)
			CHECK(f.writes[reg] == 0);
	return 0;
}

static int full_hold_precondition_failure_case(void)
{
	struct fake f;
	struct sm_io io;
	struct sm_target t = target();
	int stop_error;

	configure(&f, 0x24, 0x90, 0x16);
	f.reg[0x05] = 0x04;
	io = (struct sm_io){ .ctx = &f, .read = fake_read, .write = fake_write };
	CHECK(sm_apply_charge_hold(&io, &t, &stop_error) == -EOPNOTSUPP);
	CHECK(stop_error == 0);
	CHECK(!f.unsafe_config_write);
	CHECK((f.reg[0x08] & 0x18) == 0x08);
	CHECK(f.trace_len == 2);
	CHECK(!expect_write(&f, 0, 0x08, 0x06));
	CHECK(!expect_write(&f, 1, 0x08, 0x0e));
	for (int i = 0; i < f.trace_len; i++)
		CHECK(f.trace[i].result == 0);
	for (int reg = 0; reg < 256; reg++)
		if (reg != 0x08)
			CHECK(f.writes[reg] == 0);
	return 0;
}

static int full_hold_config_readback_failure_case(void)
{
	const unsigned int config_regs[] = {
		0x07, 0x0f, 0x00, 0x02, 0x03, 0x04
	};
	const unsigned int expected_regs[] = {
		0x08, 0x08, 0x07, 0x0f, 0x00, 0x02, 0x03, 0x04
	};
	const unsigned int expected_values[] = {
		0x06, 0x0e, 0x04, 0x0a, 0x0a, 0x05, 0x91, 0x6e
	};
	const int expected_index[] = { 2, 3, 4, 5, 6, 7 };

	for (unsigned int i = 0;
	     i < sizeof(config_regs) / sizeof(config_regs[0]); i++) {
		struct fake f;
		struct sm_io io;
		struct sm_target t = target();
		int stop_error;
		int failed_index = expected_index[i];

		configure(&f, 0x24, 0x90, 0x16);
		f.reg[0x00] = 0x01;
		f.reg[0x0f] = 0x02;
		f.reg[0x02] = 0x03;
		f.reg[0x04] = 0x01;
		f.corrupt_readback_reg = config_regs[i];
		f.corrupt_readback_value = expected_values[failed_index] ^ 0x01;
		io = (struct sm_io){ .ctx = &f, .read = fake_read, .write = fake_write };
		CHECK(sm_apply_charge_hold(&io, &t, &stop_error) == -EIO);
		CHECK(stop_error == 0);
		CHECK(!f.unsafe_config_write);
		CHECK((f.reg[0x08] & 0x18) == 0x08);
		CHECK(f.trace_len == failed_index + 1);
		for (int trace_index = 0; trace_index <= failed_index; trace_index++) {
			CHECK(!expect_write(&f, trace_index,
				expected_regs[trace_index],
				expected_values[trace_index]));
			CHECK(f.trace[trace_index].result == 0);
		}
	}
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
	if (!strcmp(argv[1], "full-hold-config-write-failure"))
		return full_hold_config_write_failure_case();
	if (!strcmp(argv[1], "full-hold-final-unpause-failure"))
		return full_hold_final_unpause_failure_case();
	if (!strcmp(argv[1], "full-hold-first-stop-failure"))
		return full_hold_first_stop_failure_case();
	if (!strcmp(argv[1], "full-hold-precondition-failure"))
		return full_hold_precondition_failure_case();
	if (!strcmp(argv[1], "full-hold-config-readback-failure"))
		return full_hold_config_readback_failure_case();
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

    def test_full_hold_asserts_complete_ordered_register_trace(self) -> None:
        self._case("full-hold-normalize")

    def test_full_hold_config_write_failure_stops_without_enabling_charge(self) -> None:
        self._case("full-hold-config-write-failure")

    def test_full_hold_final_unpause_failure_stays_in_hold(self) -> None:
        self._case("full-hold-final-unpause-failure")

    def test_full_hold_first_stop_failure_never_continues(self) -> None:
        self._case("full-hold-first-stop-failure")

    def test_full_hold_precondition_failure_never_continues(self) -> None:
        self._case("full-hold-precondition-failure")

    def test_full_hold_each_config_readback_failure_never_continues(self) -> None:
        self._case("full-hold-config-readback-failure")


if __name__ == "__main__":
    unittest.main()
