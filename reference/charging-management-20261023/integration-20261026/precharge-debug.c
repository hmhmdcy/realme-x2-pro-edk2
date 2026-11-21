
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
	if ((int)reg == f->fail_write_reg) {
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
	CHECK(f.trace_len == 9);
	CHECK(!expect_write(&f, 7, 0x08, 0x16));
	CHECK(f.trace[7].result == -EIO);
	CHECK(!expect_write(&f, 8, 0x08, 0x0e));
	CHECK(f.trace[8].result == 0);
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
	CHECK(f.trace_len == 9);
	CHECK(!expect_write(&f, 0, 0x08, 0x06));
	CHECK(!expect_write(&f, 1, 0x08, 0x0e));
	CHECK(!expect_write(&f, 2, 0x07, 0x04));
	CHECK(!expect_write(&f, 8, 0x08, 0x06));
	for (int i = 0; i < f.trace_len; i++)
		CHECK(!(f.trace[i].reg == 0x08 && (f.trace[i].value & 0x10)));
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
