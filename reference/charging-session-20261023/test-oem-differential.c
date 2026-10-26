/* SPDX-License-Identifier: GPL-2.0-only */
/* Reuse the independently extracted OEM functions and their boundary stubs.
 * This translation unit never runs the other harness's main().
 */
#define main independently_audited_reference_main
#include "../charging-oem-audit-20261023/software-full/test-reference.c"
#undef main
#include "oem-full-cycle.h"

static unsigned int compared;
static const int oem_band[] = { BATTERY_STATUS__COLD_TEMP,
	BATTERY_STATUS__LITTLE_COLD_TEMP, BATTERY_STATUS__COOL_TEMP,
	BATTERY_STATUS__LITTLE_COOL_TEMP, BATTERY_STATUS__NORMAL,
	BATTERY_STATUS__WARM_TEMP };
static const int temps[] = { -10, 10, 60, 130, 250, 450 };
static const int software_mv[] = { 3930, 4350, 4350, 4350, 4350, 4080 };
static const int float_mv[] = { 3980, 4400, 4400, 4400, 4400, 4130 };
static const int recharge_mv[] = { 3680, 4200, 4300, 4300, 4300, 4030 };

static int portable(unsigned int band, int mv, int raw_current_ma, int recharge_mode,
		    int prohibit)
{
	struct sm_oem_full_state state;
	struct sm_oem_full_sample sample = { .valid = 1, .source_known = 1,
		.online = 1, .protection_good = 1, .policy_good = 1,
		.temp_decic = temps[band], .max_cell_uv = mv * 1000,
		.gauge_current_ua = raw_current_ma * 1000,
		.cell_target_uv = float_mv[band] * 1000,
		.recharge_forbidden = prohibit };
	sm_oem_full_init(&state);
	if (recharge_mode) {
		struct sm_oem_full_sample full = sample;
		full.max_cell_uv = software_mv[band] * 1000 + 1000;
		full.hardware_full = 1;
		assert(sm_oem_full_step(&state, 0, &full).entered_full);
	}
	for (unsigned int n = 1; n <= 16; n++) {
		sm_full_ns now = (sm_full_ns)(recharge_mode ? n : n - 1) * SM_FULL_TICK_NS;
		struct sm_oem_full_result out = sm_oem_full_step(&state, now, &sample);
		if (recharge_mode ? out.recharge : out.entered_full) return n;
	}
	return 0;
}
static void compare(int actual, int expected)
{
	if (actual != expected) fprintf(stderr, "differential %u: actual%d expected%d\n", compared, actual, expected);
	assert(actual == expected);
	compared++;
}

int main(void)
{
	for (unsigned int band = 0; band < 6; band++) {
		compare(portable(band, software_mv[band], 110, 0, 0),
			sw(oem_band[band], software_mv[band], 110));
		compare(portable(band, software_mv[band] + 1, 110, 0, 0),
			sw(oem_band[band], software_mv[band] + 1, 110));
		compare(portable(band, software_mv[band] + 1, 111, 0, 0),
			sw(oem_band[band], software_mv[band] + 1, 111));
		compare(portable(band, float_mv[band] + 17, 500, 0, 0),
			hw(oem_band[band], float_mv[band] + 17));
		compare(portable(band, float_mv[band] + 18, 500, 0, 0),
			hw(oem_band[band], float_mv[band] + 18));
		compare(portable(band, recharge_mv[band], 0, 1, 0),
			recharge(oem_band[band], recharge_mv[band], 0));
		compare(portable(band, recharge_mv[band] + 1, 0, 1, 0),
			recharge(oem_band[band], recharge_mv[band] + 1, 0));
	}
	compare(portable(4, 4351, 0, 0, 0), sw(BATTERY_STATUS__NORMAL, 4351, 0));
	compare(portable(4, 4351, -1, 0, 0), sw(BATTERY_STATUS__NORMAL, 4351, -1));
	compare(portable(4, 4200, 0, 1, 1), recharge(BATTERY_STATUS__NORMAL, 4200, 1));
	const int words[] = { 0, 1, 110, 111, 0xffff, 0xff92, 0x8000 };
	gauge.cmd_addr.reg_ai = 0x0c;
	for (unsigned int i = 0; i < sizeof(words) / sizeof(words[0]); i++) {
		int ua;
		raw_current_word = words[i];
		assert(sm_oem_gauge_current_ua(words[i], &ua) == 0);
		compare(ua, -1000 * bq27541_get_average_current());
	}
	printf("{\"differential_cases\":%u,\"passed\":true}\n", compared);
	return 0;
}
