/* SPDX-License-Identifier: GPL-2.0-only */
/* Audit probe, never a charger control program. Uses the current production core. */
#include <stdio.h>
#include <assert.h>
#include "../charging-management-20261023/mp2650-core.h"

int main(void)
{
	struct sm_sample s = {
		.valid = 1, .online = 1, .protection_ok = 1,
		.budget_ua = 500000, .temp_decic = 250,
		.pack_uv = 7600000, .cell1_uv = 3800000, .cell2_uv = 3800000,
	};
	struct sm_target t;
	int ret, latched = 0;
	assert(sm_policy(&s, 4362500, 250000, 900000, &t) == 0 && t.enable);
	s.temp_decic = 530;
	ret = sm_policy(&s, 4362500, 250000, 900000, &t);
	assert(ret == -ERANGE && !t.enable);
	latched = sm_sample_latch(latched, ret, 0, 0);
	s.temp_decic = 250;
	ret = sm_policy(&s, 4362500, 250000, 900000, &t);
	latched = sm_sample_latch(latched, ret, 0, 0);
	printf("temperature_recovered_policy_ret=%d target_enable=%d latched=%d\n",
		ret, t.enable, latched);
	assert(ret == 0 && t.enable && latched);
	/* FC is not in the checked 0xc000 fault mask. The driver does not collect
	 * charger status into this sample or reset the session when it is Full. */
	s.gauge_flags = 0x0020;
	s.session_seconds = 35999;
	ret = sm_policy(&s, 4362500, 250000, 900000, &t);
	printf("attached_35999s_ret=%d target_enable=%d\n", ret, t.enable);
	assert(ret == 0 && t.enable);
	s.session_seconds = 36000;
	ret = sm_policy(&s, 4362500, 250000, 900000, &t);
	printf("attached_36000s_ret=%d target_enable=%d\n", ret, t.enable);
	assert(ret == -ETIME && !t.enable);
	return 0;
}
