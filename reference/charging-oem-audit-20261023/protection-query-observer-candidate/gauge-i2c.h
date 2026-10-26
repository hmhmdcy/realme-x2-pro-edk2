/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef SAMURAI_GAUGE_I2C_H
#define SAMURAI_GAUGE_I2C_H
#include <linux/delay.h>
#include <linux/i2c.h>
#include <linux/ktime.h>
#include "gauge-protocol.h"

/* Caller holds I2C_LOCK_SEGMENT. No other MAC client may interleave. */
static inline int sm_gauge_word_locked(struct i2c_client *g, unsigned int reg,
				       bool write, unsigned int value)
{
	union i2c_smbus_data data = { .word = value };
	int ret = __i2c_smbus_xfer(g->adapter, g->addr, g->flags,
		write ? I2C_SMBUS_WRITE : I2C_SMBUS_READ, reg,
		I2C_SMBUS_WORD_DATA, &data);
	return ret < 0 ? ret : write ? 0 : data.word;
}

/* Times and return values are observations, not pack-specific bit semantics.
 * raw[] is a complete wire frame only when full_read is true. Incomplete
 * transfers cannot provide a valid 36-byte frame, even if the buffer changed.
 */
struct sm_mac_receipt {
	unsigned int command;
	int expected_size, select_rc, read_rc, validate_rc;
	bool attempted, select_attempted, read_attempted, full_read, validate_attempted;
	u64 started_ns, select_end_ns, read_end_ns, ended_ns;
	unsigned char raw[36];
};

static inline int sm_gauge_mac_transfer_locked(struct i2c_client *g,
	unsigned int command, unsigned char *packet, int size,
	struct sm_mac_receipt *receipt)
{
	unsigned char start = 0x3e;
	struct i2c_msg messages[] = {
		{ .addr = g->addr, .len = 1, .buf = &start },
		{ .addr = g->addr, .flags = I2C_M_RD, .len = 36, .buf = packet },
	};
	int ret;

	if (receipt) {
		receipt->attempted = true;
		receipt->started_ns = ktime_get_boottime_ns();
	}
	if (size < 0) { ret = size; goto out; }
	if (receipt) receipt->select_attempted = true;
	ret = sm_gauge_word_locked(g, 0x3e, true, command);
	if (receipt) {
		receipt->select_rc = ret;
		receipt->select_end_ns = ktime_get_boottime_ns();
	}
	if (ret) goto out;
	usleep_range(1000, 1500); /* unchanged OEM query delay */
	if (receipt) receipt->read_attempted = true;
	ret = __i2c_transfer(g->adapter, messages, ARRAY_SIZE(messages));
	if (receipt) {
		receipt->read_rc = ret;
		receipt->read_end_ns = ktime_get_boottime_ns();
	}
	if (ret != ARRAY_SIZE(messages)) { ret = ret < 0 ? ret : -EIO; goto out; }
	if (receipt) receipt->full_read = receipt->validate_attempted = true;
	ret = sm_mac_validate_sized(packet, 36, command, size);
	if (receipt) receipt->validate_rc = ret;
out:
	if (receipt) receipt->ended_ns = ktime_get_boottime_ns();
	return ret;
}

/* Existing API retains its exact six-command allowlist and error policy. */
static inline int sm_gauge_mac_locked(struct i2c_client *g, unsigned int command,
				      unsigned char *packet)
{
	return sm_gauge_mac_transfer_locked(g, command, packet,
					   sm_mac_data_size(command), NULL);
}

/* Caller holds the same I2C_LOCK_SEGMENT as normal MAC clients. */
static inline int sm_gauge_mac_observe_locked(struct i2c_client *g,
	unsigned int command, struct sm_mac_receipt *receipt)
{
	if (!receipt) return -EINVAL;
	*receipt = (struct sm_mac_receipt){ .command = command,
		.expected_size = sm_mac_observe_data_size(command) };
	return sm_gauge_mac_transfer_locked(g, command, receipt->raw,
					   receipt->expected_size, receipt);
}
#endif
