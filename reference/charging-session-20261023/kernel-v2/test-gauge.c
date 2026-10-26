/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include "mp2650-core.h"
#include "gauge-protocol.h"
#include "oem-full-cycle.h"

#define I2C_LOCK_SEGMENT 1
struct i2c_client { void *adapter; };
struct sm_charger { struct i2c_client *gauge; };
static int lock_depth, lock_count, unlock_count, reads, mac_reads, error_reg, mac_error;
static int current_word;
static unsigned int assertions, sequences;
#define CHECK(x) do { assert(x); assertions++; } while (0)
static void i2c_lock_bus(void *adapter, int kind)
{ assert(adapter && kind == 1 && lock_depth == 0); lock_depth++; lock_count++; }
static void i2c_unlock_bus(void *adapter, int kind)
{ assert(adapter && kind == 1 && lock_depth == 1); lock_depth--; unlock_count++; }
static int sm_gauge_word_locked(struct i2c_client *g, int reg, bool unused, int delay)
{
	const int expected[] = { 6, 8, 0x0a, 0x0c };
	assert(g && lock_depth == 1 && !unused && delay == 0);
	assert(reads < 4 && reg == expected[reads++]);
	if (reg == error_reg) return -EREMOTEIO;
	return reg == 6 ? 2981 : reg == 8 ? 8610 : reg == 0x0a ? 0 : current_word;
}
static int sm_gauge_mac_locked(struct i2c_client *g, int command, unsigned char *packet)
{
	assert(g && lock_depth == 1 && command == 0x71);
	mac_reads++;
	if (mac_error) return -EBADMSG;
	memset(packet, 0, 36);
	packet[2] = 4300 & 255; packet[3] = 4300 >> 8;
	packet[4] = 4310 & 255; packet[5] = 4310 >> 8;
	return 0;
}

/* Reproduce Linux's identifier macro to catch accidental local `current`. */
#define current fake_get_current()
#include "gauge-extracted.inc"
#undef current

static void reset(void)
{
	lock_depth = lock_count = unlock_count = reads = mac_reads = mac_error = 0;
	error_reg = -1; current_word = 110;
}
int main(void)
{
	struct i2c_client gauge = { &gauge };
	struct sm_charger c = { &gauge };
	struct sm_sample sample = { 0 };
	sequences++; reset();
	CHECK(sm_gauge_sample(&c, &sample) == 0);
	CHECK(sample.gauge_current_ua == 110000 && sample.temp_decic == 250);
	CHECK(sample.cell1_uv == 4300000 && sample.cell2_uv == 4310000 && sample.pack_uv == 8610000);
	CHECK(lock_count == 1 && unlock_count == 1 && lock_depth == 0 && mac_reads == 1);
	sequences++; reset(); current_word = 0xffff;
	CHECK(sm_gauge_sample(&c, &sample) == 0 && sample.gauge_current_ua == -1000);
	CHECK(reads == 4 && lock_depth == 0);
	const int failure[] = { 6, 8, 0x0a, 0x0c };
	for (unsigned int i = 0; i < 4; i++) {
		sequences++; reset(); sample = (struct sm_sample){ 0 }; error_reg = failure[i];
		CHECK(sm_gauge_sample(&c, &sample) == -EREMOTEIO);
		CHECK(lock_count == 1 && unlock_count == 1 && lock_depth == 0 && mac_reads == 0);
		CHECK(!sample.valid && sample.gauge_current_ua == 0);
	}
	sequences++; reset(); sample = (struct sm_sample){ 0 }; mac_error = 1;
	CHECK(sm_gauge_sample(&c, &sample) == -EBADMSG && !sample.valid);
	CHECK(sample.gauge_current_ua == 0 && lock_depth == 0);
	printf("{\"gauge_sequences\":%u,\"assertions\":%u,\"passed\":true}\n", sequences, assertions);
	return 0;
}
