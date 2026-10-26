/* Existing packets and actual safe OEM functions; no bus interface. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "../../charging-management-20261023/gauge-protocol.h"
#include "../../charging-session-20261023/kernel-v2/mp2650-core.h"
#include "../../charging-session-20261023/kernel-v2/oem-full-cycle.h"
#include "../../charging-session-20261023/kernel-v2/charge-cycle.h"

typedef unsigned char u8;
static u8 packet[36];
static unsigned int selected, calls;
static void bq27541_i2c_txsubcmd(unsigned int reg, unsigned int command)
{
	assert(reg == 0x3e && (command == 0x54 || command == 0x57));
	assert(sm_le16(packet) == command); selected = command; calls++;
}
static void bq27541_read_i2c_block(unsigned int reg, unsigned int len, u8 *out)
{
	assert(reg == 0x3e && len == 4 && selected == sm_le16(packet));
	memcpy(out, packet, len);
}
#define pr_err(...) ((void)0)
#define BIT(n) (1U << (n))
#define usleep_range(a,b) assert((a) == 10000 && (b) == 10000)
#define msleep(a) assert((a) == 1000)
#include "oem-query-extracted.inc"

int main(int argc, char **argv)
{
	unsigned int packets = 0, cases = 0, values[5] = {0};
	unsigned int cmds[] = {1, 0x51, 0x53, 0x54, 0x57, 0x71};
	u8 command[2];
	assert(argc == 2);
	FILE *f = fopen(argv[1], "rb"); assert(f);
	for (unsigned int i = 0; i < 6; i++) {
		assert(fread(command, 1, 2, f) == 2 && sm_le16(command) == cmds[i]);
		assert(fread(packet, 1, 36, f) == 36 && !sm_mac_validate(packet, 36, cmds[i]));
		packets++; cases++;
		if (i < 5) values[i] = sm_mac_data_size(cmds[i]) == 2 ? sm_le16(packet+2) : sm_le32(packet+2);
		if (cmds[i] == 0x54) { assert(bq8z610_sealed() == 1); cases++; }
		if (cmds[i] == 0x57) { assert(bq8z610_check_gauge_enable() == 1); cases++; }
	}
	assert(fgetc(f) == EOF); fclose(f);
	assert(calls == 2);
	assert(values[0] == 0x2719 && values[1] == 0 && values[2] == 0 && values[3] == 0x386 && values[4] == 0x18);
	assert(!sm_gauge_protection_state(values[0], values[1], values[2], values[3], values[4])); cases++;
	assert(!(values[4] & 0x40)); cases++;
	assert(sm_mac_data_size(0x50) == -EINVAL && sm_mac_data_size(0x52) == -EINVAL && sm_mac_data_size(0x56) == -EINVAL); cases++;
	/* The following are explicit hypothetical bit-state vectors, not newly
	 * observed packets, status events, thresholds or physical acceptance. */
	struct sm_sample sample = { .valid=1, .online=1, .protection_ok=1,
		.budget_ua=100000, .temp_decic=268, .pack_uv=8598000,
		.cell1_uv=4300000, .cell2_uv=4298000, .gauge_flags=0xc0 };
	struct sm_target target;
	enum sm_policy_reason reason;
	assert(!sm_policy_with_reason(&sample, 4362500, 250000, 900000, &target, &reason)); cases++;
	sample.gauge_flags |= 0x4000;
	int ret = sm_policy_with_reason(&sample, 4362500, 250000, 900000, &target, &reason);
	assert(ret == -EAGAIN && reason == SM_POLICY_REASON_GAUGE_CHARGE_STOP && !target.enable); cases++;
	assert(!sm_sample_latch(0, ret, reason == SM_POLICY_REASON_GAUGE_CHARGE_STOP, 0)); cases++;
	assert(sm_sample_latch(1, ret, 1, 0)); cases++;
	assert(!sm_cycle_full_allowed(1, 0, ret)); cases++;
	sample.gauge_flags |= 0x8000;
	assert(sm_policy_with_reason(&sample, 4362500, 250000, 900000, &target, &reason) == -EIO && reason == SM_POLICY_REASON_NONE); cases++;
	sample.gauge_flags &= ~0x8000;
	sample.session_seconds = SM_CYCLE_LIMIT_SECONDS;
	assert(sm_policy_with_reason(&sample, 4362500, 250000, 900000, &target, &reason) == -ETIME && reason == SM_POLICY_REASON_NONE); cases++;
	sample.session_seconds = 0; sample.protection_ok = 0;
	assert(sm_policy_with_reason(&sample, 4362500, 250000, 900000, &target, &reason) == -ENODATA && reason == SM_POLICY_REASON_NONE); cases++;
	struct sm_oem_full_state full;
	struct sm_oem_full_sample in = { .valid=1, .source_known=1, .online=1,
		.protection_good=1, .policy_good=1, .hardware_full=1, .temp_decic=268,
		.max_cell_uv=4350000, .cell_target_uv=4362500, .gauge_flags=0x4000 };
	sm_oem_full_init(&full);
	struct sm_oem_full_result out = sm_oem_full_step(&full, 0, &in);
	assert(out.stop_all && out.block == SM_FULL_TCA_HOLD && !out.entered_full && !out.full && !out.recharge); cases++;
	full.full=1; full.cause=SM_FULL_HARDWARE;
	out = sm_oem_full_step(&full, 5000000000ULL, &in);
	assert(out.stop_all && full.full && !out.hold_charge_only && !out.recharge); cases++;
	printf("{\"passed\":true,\"real_packet_count\":%u,\"directed_checks\":%u,\"actual_oem_functions_executed\":2,\"new_packet_generation\":0}\n", packets, cases);
	return 0;
}
