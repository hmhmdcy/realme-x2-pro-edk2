/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>
#include "mp2650-core.h"

static int policy_cases, io_cases;
struct mock {
	unsigned char reg[256];
	int op, writes, fail_at, persistent, lose_ack;
	int corrupt_after_write, corrupt_pending;
};

static struct mock initial(void)
{
	struct mock m = { 0 };
	m.reg[0] = m.reg[0x0f] = 0x92;
	m.reg[2] = 0x86; m.reg[3] = 0xa2; m.reg[4] = 0xe9;
	m.reg[5] = 3; m.reg[7] = 0x14; m.reg[8] = 0x16; m.reg[9] = 0x4c;
	return m;
}

static int fail(struct mock *m)
{
	m->op++;
	return m->fail_at && (m->op == m->fail_at ||
		(m->persistent && m->op >= m->fail_at));
}

static int read_reg(void *ctx, unsigned int reg)
{
	struct mock *m = ctx;
	if (fail(m)) return -EREMOTEIO;
	if (m->corrupt_pending) {
		m->corrupt_pending = 0;
		return m->reg[reg] ^ 0x40;
	}
	return m->reg[reg];
}

static int write_reg(void *ctx, unsigned int reg, unsigned int value)
{
	struct mock *m = ctx;
	int failed = fail(m);
	unsigned int mask = reg == 8 ? 0x18 : reg == 3 ? 0xff : 0x7f;

	assert(reg == 0 || reg == 0x0f || reg == 2 || reg == 3 || reg == 4 || reg == 8);
	assert(!((value ^ m->reg[reg]) & ~mask));
	if (reg == 8) assert(!(value & 0xc0));
	else assert((m->reg[8] & 0x18) == 8); /* input converter suspended */
	if (failed && !m->lose_ack) return -EREMOTEIO;
	m->reg[reg] = value;
	m->writes++;
	if (m->writes == m->corrupt_after_write) m->corrupt_pending = 1;
	return failed ? -EREMOTEIO : 0;
}

static struct sm_sample sample(void)
{
	return (struct sm_sample){ .valid = 1, .online = 1, .protection_ok = 1,
		.budget_ua = 1500000, .temp_decic = 250, .pack_uv = 7600000,
		.cell1_uv = 3800000, .cell2_uv = 3800000 };
}

static int policy(struct sm_sample s, struct sm_target *t)
{
	policy_cases++;
	return sm_policy(&s, 4362500, 1100000, 2000000, t);
}

static void policy_tests(void)
{
	struct sm_sample s;
	struct sm_target t;
	int temp, budget, ret;
	/* Independent acceptance intervals reconstructed from the OEM DTS. */
	for (temp = -1000; temp <= 1500; temp++) {
		s = sample(); s.temp_decic = temp;
		ret = policy(s, &t);
		if (temp < -20 || temp >= 530) { assert(ret == -ERANGE); continue; }
		assert(!ret && t.enable);
		assert(t.current_ua == (temp < 0 ? 250000 : temp < 50 ? 900000 :
					 temp < 440 ? 1100000 : 550000));
		assert(t.cell_uv <= (temp < 0 ? 3980000 : temp < 440 ? 4362500 : 4130000));
	}
	for (budget = -1; budget <= 3500000; budget += 1001) {
		s = sample(); s.budget_ua = budget;
		ret = policy(s, &t);
		if (budget < 50000) assert(ret == -ENODATA);
		else assert(!ret && t.input_ua <= budget && t.input_ua <= 2000000);
	}
	s = sample(); s.budget_ua = INT_MAX;
	assert(!policy(s, &t) && t.input_ua == 2000000);
	s = sample(); s.valid = 0; assert(policy(s, &t) == -ENODATA && !t.enable);
	s = sample(); s.protection_ok = 0; assert(policy(s, &t) == -ENODATA);
	s = sample(); s.online = 0; assert(!policy(s, &t) && !t.enable);
	s = sample(); s.session_seconds = 36000; assert(policy(s, &t) == -ETIME);
	s = sample(); s.session_seconds = 35999; assert(!policy(s, &t));
	s = sample(); s.cell1_uv = 4420000; s.cell2_uv = 3180000;
	assert(policy(s, &t) == -EOVERFLOW); /* pack / 2 would conceal this */
	s = sample(); s.pack_uv = 8000000; assert(policy(s, &t) == -ENODATA);
	s = sample(); s.cell1_uv = 0; assert(policy(s, &t) == -ERANGE);
	s = sample(); s.gauge_flags = 0x8000; assert(policy(s, &t) == -EIO);
	for (int bit = 0; bit < 8; bit++) {
		s = sample(); s.fault = 1 << bit; assert(policy(s, &t) == -EIO);
	}
	s = sample(); assert(sm_policy(&s, 3700000, 1100000, 2000000, &t) == -ERANGE);
	assert(sm_policy(&s, 4362500, 50000, 2000000, &t) == -ENODATA);
	assert(!sm_policy(&s, 4200000, 200000, 975000, &t));
	assert(t.cell_uv <= 4200000 && t.current_ua == 200000 && t.input_ua == 950000);
}

static void transaction_tests(void)
{
	struct sm_target target = { 1, 500000, 900000, 4362500 };
	struct mock m = initial();
	struct sm_io io = { &m, read_reg, write_reg };
	int stop, ops, writes;

	assert(!sm_apply(&io, &target, &stop) && !stop);
	ops = m.op; writes = m.writes;
	assert((m.reg[0] & 0x7f) == 10 && (m.reg[0x0f] & 0x7f) == 10);
	assert((m.reg[2] & 0x7f) == 18 && m.reg[3] == 0x31);
	assert((m.reg[4] & 0x7f) == 0x68 && m.reg[9] == 0x4c);
	assert((m.reg[8] & 0x18) == 0x10);
	assert(!sm_apply(&io, &target, &stop) && m.writes == writes);
	io_cases += 2;
	/* Every transaction operation: single fault; persistent bus loss; lost ACK
	 * after an effective write. A recovered bus must prove the paused state.
	 */
	for (int mode = 0; mode < 3; mode++)
		for (int n = 1; n <= ops; n++) {
			m = initial(); m.fail_at = n;
			m.persistent = mode == 1; m.lose_ack = mode == 2;
			assert(sm_apply(&io, &target, &stop) < 0);
			if (mode == 1) assert(stop < 0);
			else assert(!stop && (m.reg[8] & 0x18) == 8);
			io_cases++;
		}
	for (int n = 1; n <= writes; n++) {
		m = initial(); m.corrupt_after_write = n;
		assert(sm_apply(&io, &target, &stop) == -EIO);
		assert(!stop && (m.reg[8] & 0x18) == 8);
		io_cases++;
	}
	m = initial(); m.reg[8] |= 0x20; assert(sm_preconditions(&io) == -EOPNOTSUPP);
	m = initial(); m.reg[8] &= ~4; assert(sm_preconditions(&io) == -EOPNOTSUPP);
	m = initial(); m.reg[5] |= 4; assert(sm_preconditions(&io) == -EOPNOTSUPP);
	m = initial(); m.reg[9] |= 0x10; assert(sm_preconditions(&io) == -EOPNOTSUPP);
	m = initial(); m.reg[9] &= ~8; assert(sm_preconditions(&io) == -EOPNOTSUPP);
	m = initial(); m.reg[7] |= 0x40; assert(sm_preconditions(&io) == -EOPNOTSUPP);
	io_cases += 6;
	m = initial(); assert(sm_update(&io, 8, 0x80, 0x80) == -EINVAL);
	assert(sm_update(&io, 8, 0x02, 0) == -EINVAL);
	assert(sm_update(&io, 9, 0x30, 0) == -EINVAL && m.writes == 0);
	io_cases += 3;
	m = initial(); target.enable = 0;
	assert(!sm_apply(&io, &target, &stop) && (m.reg[8] & 0x18) == 8);
	m = initial(); m.fail_at = 1; m.persistent = 1;
	assert(sm_apply(&io, &target, &stop) < 0 && stop < 0);
	/* Honest failure evidence: with a dead bus the hardware may still charge. */
	assert((m.reg[8] & 0x18) == 0x10);
	io_cases += 2;
}

int main(void)
{
	int latch = 0;
	/* Real session ordering: unknown SDP allowance, configured budget,
	 * suspend, resume, electrical IO fault, then further source transitions.
	 */
	latch = sm_sample_latch(latch, -ENODATA, 1, 0); assert(!latch);
	latch = sm_sample_latch(latch, 0, 0, 0); assert(!latch);
	latch = sm_sample_latch(latch, -ENODATA, 1, 0); assert(!latch);
	latch = sm_sample_latch(latch, 0, 0, 0); assert(!latch);
	latch = sm_sample_latch(latch, -EIO, 0, 0); assert(latch);
	latch = sm_sample_latch(latch, -ENODATA, 1, 0); assert(latch);
	latch = sm_sample_latch(latch, 0, 0, 0); assert(latch);
	assert(sm_sample_latch(0, -ENODATA, 1, 4));
	policy_tests(); transaction_tests();
	printf("{\"source_latch_sequence_cases\":8,\"policy_cases\":%d,\"transaction_cases\":%d,\"passed\":true}\n",
	       policy_cases, io_cases);
	return 0;
}
