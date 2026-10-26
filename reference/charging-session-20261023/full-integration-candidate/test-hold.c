/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "mp2650-core.h"

struct write { int reg, value, failed; };
struct bus {
	int reg[256], reads, writes, fail_write, primary_error, failed;
	int fail_read, fail_read_after_error;
	struct write log[64];
};
static unsigned int assertions, sequences;
#define CHECK(x) do { int check_once = !!(x); if (!check_once) fprintf(stderr, "line %d: %s\n", __LINE__, #x); assert(check_once); assertions++; } while (0)

static int read_reg(void *ctx, unsigned int reg)
{
	struct bus *b = ctx;
	b->reads++;
	if (b->reads == b->fail_read || (b->failed && b->fail_read_after_error && reg == 8))
		return -EREMOTEIO;
	return b->reg[reg];
}
static int write_reg(void *ctx, unsigned int reg, unsigned int value)
{
	struct bus *b = ctx;
	assert(b->writes < 64);
	struct write *w = &b->log[b->writes++];
	*w = (struct write){ reg, value, b->writes == b->fail_write };
	if (w->failed) {
		b->failed = 1;
		return b->primary_error;
	}
	b->reg[reg] = value;
	return 0;
}
static void reset(struct bus *b)
{
	*b = (struct bus){ .reg = { [0] = 10, [0x0f] = 10, [2] = 5,
		[3] = 0, [4] = 0x68, [5] = 0, [7] = 0, [8] = 0x16, [9] = 0x48 },
		.primary_error = -ETIMEDOUT };
}
static void no_pulse(const struct bus *b)
{
	for (int i = 0; i < b->writes; i++)
		CHECK(b->log[i].reg != 8 || !(b->log[i].value & 0x10));
}

int main(void)
{
	struct bus b;
	struct sm_io io = { &b, read_reg, write_reg };
	struct sm_target hold = { .enable = 0, .input_ua = 100000,
		.current_ua = 300000, .cell_uv = 4350000 };
	int stop_error, written;

	/* Every changed field is programmed with charge already off and input
	 * paused, then only the converter is released. No CHG pulse is allowed.
	 */
	sequences++; reset(&b);
	CHECK(sm_apply_charge_hold(&io, &hold, &stop_error) == 0 && stop_error == 0);
	written = b.writes;
	CHECK(written == 8);
	CHECK(b.log[0].reg == 8 && b.log[0].value == 0x06);
	CHECK(b.log[1].reg == 8 && b.log[1].value == 0x0e);
	CHECK(b.reg[0] == 2 && b.reg[0x0f] == 2 && b.reg[2] == 6 && b.reg[4] == 0x66);
	CHECK(b.reg[8] == 0x06 && b.reg[9] == 0x48 && b.reg[7] == 0 && b.reg[5] == 0);
	for (int i = 2; i < written - 1; i++) CHECK(b.log[i].reg != 8);
	no_pulse(&b);
	/* Stable Full has no register writes at all, including LEARN toggles. */
	sequences++;
	b.writes = b.reads = 0;
	CHECK(sm_apply_charge_hold(&io, &hold, &stop_error) == 0 && stop_error == 0);
	CHECK(b.writes == 0 && b.reg[8] == 0x06);

	/* Starting from an input inhibit must also never briefly enable CHG. */
	sequences++;
	b.reg[8] = 0x0e;
	CHECK(sm_apply_charge_hold(&io, &hold, &stop_error) == 0 && b.reg[8] == 0x06);
	no_pulse(&b);

	/* Each real write can fail: primary errno is retained, fallback stops,
	 * and no path restores the earlier larger input limit or enables CHG.
	 */
	for (int failure = 1; failure <= written; failure++) {
		sequences++; reset(&b); b.fail_write = failure;
		CHECK(sm_apply_charge_hold(&io, &hold, &stop_error) == -ETIMEDOUT);
		CHECK(stop_error == 0 && (b.reg[8] & 0x18) == 8);
		CHECK(b.reg[0] <= 10 && b.reg[0x0f] <= 10 && b.reg[9] == 0x48);
		no_pulse(&b);
	}
	/* Persistent read failure after the primary write fault preserves both. */
	sequences++; reset(&b); b.fail_write = 3; b.fail_read_after_error = 1;
	CHECK(sm_apply_charge_hold(&io, &hold, &stop_error) == -ETIMEDOUT);
	CHECK(stop_error == -EREMOTEIO);
	no_pulse(&b);
	/* Failure reading the initial CHG clear still takes the stop fallback. */
	sequences++; reset(&b); b.fail_read = 1;
	CHECK(sm_apply_charge_hold(&io, &hold, &stop_error) == -EREMOTEIO);
	CHECK(stop_error == 0 && (b.reg[8] & 0x18) == 8);
	no_pulse(&b);
	/* Invalid requests stop rather than retaining a previously charging mode. */
	sequences++; reset(&b); hold.input_ua = 99999;
	CHECK(sm_apply_charge_hold(&io, &hold, &stop_error) == -EINVAL);
	CHECK(stop_error == 0 && (b.reg[8] & 0x18) == 8);
	no_pulse(&b);
	printf("{\"hold_sequences\":%u,\"assertions\":%u,\"writes_under_fault\":%d,\"passed\":true}\n", sequences, assertions, written);
	return 0;
}
