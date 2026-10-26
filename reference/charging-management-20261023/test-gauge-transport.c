/* SPDX-License-Identifier: GPL-2.0-only */
/* Exercise the production transport header, substituting only Linux I2C/delay.
 * The six packet fixtures are the retained, already validated device replies.
 */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include "gauge-i2c.h"

static struct i2c_adapter adapter;
static struct i2c_client gauge = { .adapter = &adapter, .addr = 0x55, .flags = 0 };
static unsigned char response[36];
static char events[8];
static unsigned int event_count, expected_command, expected_reg, expected_value;
static int smbus_result, transfer_result, word_response;
static bool word_mode, expected_write, segment_locked;
static unsigned int cases, packets, failures, forbidden;

static void record(char event)
{
	assert(segment_locked);
	assert(event_count + 1 < sizeof(events));
	events[event_count++] = event;
	events[event_count] = 0;
}

int __i2c_smbus_xfer(struct i2c_adapter *bus, unsigned short addr,
	unsigned short flags, char direction, unsigned char command,
	int size, union i2c_smbus_data *data)
{
	assert(bus == &adapter && addr == 0x55 && flags == 0);
	assert(size == I2C_SMBUS_WORD_DATA);
	if (word_mode) {
		assert(command == expected_reg);
		assert(direction == (expected_write ? I2C_SMBUS_WRITE : I2C_SMBUS_READ));
		if (expected_write) assert(data->word == expected_value);
		else data->word = word_response;
	} else {
		/* The only write is a whitelisted, read-only MAC query selector. */
		assert(direction == I2C_SMBUS_WRITE && command == 0x3e);
		assert(data->word == expected_command && sm_mac_data_size(data->word) > 0);
	}
	record(direction == I2C_SMBUS_WRITE ? 'W' : 'Q');
	return smbus_result;
}

void usleep_range(unsigned long minimum, unsigned long maximum)
{
	assert(!word_mode && minimum == 1000 && maximum == 1500);
	assert(!strcmp(events, "W"));
	record('D');
}

int __i2c_transfer(struct i2c_adapter *bus, struct i2c_msg *messages, int count)
{
	assert(!word_mode && bus == &adapter && count == 2);
	assert(!strcmp(events, "WD"));
	assert(messages[0].addr == 0x55 && messages[0].flags == 0);
	assert(messages[0].len == 1 && messages[0].buf[0] == 0x3e);
	assert(messages[1].addr == 0x55 && messages[1].flags == I2C_M_RD);
	assert(messages[1].len == sizeof(response));
	record('R');
	if (transfer_result == 2) memcpy(messages[1].buf, response, sizeof(response));
	return transfer_result;
}

static void reset(void)
{
	memset(events, 0, sizeof(events)); event_count = 0;
	smbus_result = 0; transfer_result = 2;
	word_mode = false; segment_locked = true;
}

static void query(unsigned int command, int expected, const char *trace)
{
	struct { unsigned char before[16], data[36], after[16]; } buffer;
	memset(&buffer, 0xa5, sizeof(buffer));
	expected_command = command;
	assert(sm_gauge_mac_locked(&gauge, command, buffer.data) == expected);
	assert(!strcmp(events, trace)); /* No hidden retry/fallback after a fault. */
	for (unsigned int i = 0; i < 16; i++)
		assert(buffer.before[i] == 0xa5 && buffer.after[i] == 0xa5);
	if (expected == 0) assert(!memcmp(buffer.data, response, sizeof(response)));
	cases++; if (expected < 0) failures++;
}

int main(int argc, char **argv)
{
	const int errors[] = { -EIO, -ENXIO, -EREMOTEIO, -ETIMEDOUT, -EBUSY, -EAGAIN };
	const unsigned int denied[] = { 0, 2, 0x0f, 0x10, 0x1f, 0x20, 0x23,
		0x30, 0x61, 0xf00, 0x3672, 0xffff, 0x10001 };
	unsigned char command_bytes[2], original[36];
	FILE *fixture;
	assert(argc == 2); fixture = fopen(argv[1], "rb"); assert(fixture);
	while (fread(command_bytes, 1, 2, fixture) == 2) {
		unsigned int command = sm_le16(command_bytes);
		assert(fread(original, 1, sizeof(original), fixture) == sizeof(original));
		assert(!sm_mac_validate(original, sizeof(original), command));
		packets++; memcpy(response, original, sizeof(response));
		reset(); query(command, 0, "WDR");
		for (unsigned int i = 0; i < ARRAY_SIZE(errors); i++) {
			reset(); smbus_result = errors[i]; query(command, errors[i], "W");
			reset(); transfer_result = errors[i]; query(command, errors[i], "WDR");
		}
		for (int short_transfer = 0; short_transfer < 2; short_transfer++) {
			reset(); transfer_result = short_transfer; query(command, -EIO, "WDR");
		}
		/* Reject stale, corrupted, and truncated-looking successful transfers. */
		reset(); response[0] ^= 1; query(command, -EAGAIN, "WDR");
		memcpy(response, original, sizeof(response));
		reset(); response[2] ^= 1; query(command, -EBADMSG, "WDR");
		memcpy(response, original, sizeof(response));
		reset(); response[34] ^= 1; query(command, -EBADMSG, "WDR");
		memcpy(response, original, sizeof(response));
		reset(); response[35]--; query(command, -EMSGSIZE, "WDR");
		memcpy(response, original, sizeof(response));
		reset(); query(command, 0, "WDR"); /* Recovery reads new data. */
	}
	assert(feof(fixture) && !ferror(fixture)); fclose(fixture); assert(packets == 6);
	for (unsigned int i = 0; i < ARRAY_SIZE(denied); i++) {
		reset(); query(denied[i], -EINVAL, ""); forbidden++;
	}
	/* The real temperature, pack-voltage and flags word-read transport. */
	for (unsigned int reg = 6; reg <= 10; reg += 2) {
		reset(); word_mode = true; expected_write = false; expected_reg = reg;
		word_response = reg == 6 ? 3011 : reg == 8 ? 8658 : 0x80;
		assert(sm_gauge_word_locked(&gauge, reg, false, 0) == word_response);
		assert(!strcmp(events, "Q")); cases++;
		for (unsigned int i = 0; i < ARRAY_SIZE(errors); i++) {
			reset(); word_mode = true; expected_write = false; expected_reg = reg;
			smbus_result = errors[i];
			assert(sm_gauge_word_locked(&gauge, reg, false, 0) == errors[i]);
			assert(!strcmp(events, "Q")); cases++; failures++;
		}
	}
	printf("{\"passed\":true,\"captured_packets\":%u,\"transport_cases\":%u,"
	       "\"rejected_error_cases\":%u,\"forbidden_commands_without_bus_access\":%u}\n",
	       packets, cases, failures, forbidden);
	return 0;
}
