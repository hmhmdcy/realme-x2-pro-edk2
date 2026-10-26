/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdio.h>
#include "charge-cycle.h"
#include "../charging-management-20261023/mp2650-core.h"

#define NS(x) ((sm_cycle_ns)(x) * 1000000000ULL)
static unsigned int cases;
#define CHECK(expression) do { assert(expression); cases++; } while (0)

int main(void)
{
	struct sm_charge_cycle c;

	/* A cold boot is OEM-compatible: no persistent RTC or new unplug gate. */
	sm_cycle_init(&c, NS(500));
	CHECK(sm_cycle_update(&c, NS(500), -1, 0) == 0 && !c.attached);
	CHECK(sm_cycle_update(&c, NS(500), 1, 0) == 0 && c.attached);
	CHECK(sm_cycle_update(&c, NS(510), 1, 0) == 10);
	/* BOOTTIME includes suspend; service restart never initializes this state. */
	CHECK(sm_cycle_update(&c, NS(530), -1, 0) == 30);
	CHECK(sm_cycle_update(&c, NS(600), 1, 0) == 100);

	/* Full can remain on the cable for days without a lifetime timeout. */
	for (unsigned int day = 0; day < 10; day++) {
		CHECK(sm_cycle_update(&c, NS(600 + day * 86400ULL), 1, 1) == 0);
		CHECK(!c.timed_out);
	}
	/* Automatic recharge starts a new OEM period from the last confirmed Full. */
	CHECK(sm_cycle_update(&c, NS(600 + 9 * 86400ULL + 5), 1, 0) == 5);
	CHECK(sm_cycle_update(&c, NS(600 + 9 * 86400ULL + 35999), 1, 0) == 35999);
	CHECK(sm_cycle_update(&c, NS(600 + 9 * 86400ULL + 36000), 1, 0) == 36000);
	CHECK(c.timed_out);
	/* Once established, true timeout survives Full, unknown source and AUTO. */
	CHECK(sm_cycle_update(&c, c.last_ns + NS(1), 1, 1) == 36000);
	CHECK(sm_cycle_update(&c, c.last_ns + NS(1), -1, 1) == 36000);
	CHECK(sm_cycle_update(&c, c.last_ns + NS(1), 1, 0) == 36000);
	CHECK(sm_cycle_update(&c, c.last_ns + NS(1), 0, 0) == 0 && !c.timed_out);
	CHECK(sm_cycle_update(&c, c.last_ns + NS(1), 1, 0) == 0);

	/* Unknown/corrupt/incomplete Full evidence must be passed as full_good=0. */
	CHECK(sm_cycle_update(&c, c.last_ns + NS(10), 1, 0) == 10);
	CHECK(sm_cycle_update(&c, c.last_ns + NS(10), -1, 1) == 20);
	CHECK(sm_cycle_update(&c, c.last_ns + NS(10), 1, 0) == 30);
	CHECK(sm_cycle_update(&c, c.last_ns + NS(1), 1, 1) == 0);
	CHECK(sm_cycle_update(&c, c.last_ns + NS(1), 1, 0) == 1);

	/* A reversed input clock does not wrap into a free/new cycle. */
	CHECK(sm_cycle_update(&c, c.last_ns - 1, 1, 1) == 36000);
	CHECK(c.timed_out);
	CHECK(sm_cycle_update(&c, c.last_ns + 1, 1, 1) == 36000);
	CHECK(sm_cycle_update(&c, c.last_ns + 2, 0, 0) == 0);

	/* ns arithmetic does not overflow when close to UINT64_MAX. */
	sm_cycle_init(&c, UINT64_MAX - NS(100));
	CHECK(sm_cycle_update(&c, UINT64_MAX - NS(100), 1, 0) == 0);
	CHECK(sm_cycle_update(&c, UINT64_MAX, 1, 0) == 100);
	const unsigned int boundaries[] = { 0, 1, 60, 35998, 35999, 36000, 36001, 36010, UINT32_MAX };
	for (unsigned int i = 0; i < sizeof(boundaries) / sizeof(boundaries[0]); i++) {
		unsigned int second = boundaries[i];
		sm_cycle_init(&c, NS(19));
		CHECK(sm_cycle_update(&c, NS(19), 1, 0) == 0);
		CHECK(sm_cycle_update(&c, NS(19ULL + second), 1, 0) ==
		      (second < 36000 ? second : 36000));
	}

	/* Exercise Full authorization through the actual existing policy, rather
	 * than pretending SOC=100 or net current=0 proves charger completion.
	 */
	struct sm_sample good = { .valid = 1, .online = 1, .protection_ok = 1,
		.budget_ua = 500000, .temp_decic = 250, .pack_uv = 8600000,
		.cell1_uv = 4300000, .cell2_uv = 4300000 };
	struct sm_target target;
	CHECK(sm_policy(&good, 4362500, 250000, 900000, &target) == 0);
	CHECK(sm_cycle_full_allowed(1, 0, 0));
	CHECK(!sm_cycle_full_allowed(0, 0, 0));
	CHECK(!sm_cycle_full_allowed(1, 1, 0));
	CHECK(!sm_cycle_full_allowed(1, 0, -EIO));
	for (unsigned int fault = 0; fault < 10; fault++) {
		struct sm_sample bad = good;
		switch (fault) {
		case 0: bad.valid = 0; break;
		case 1: bad.protection_ok = 0; break;
		case 2: bad.budget_ua = 0; break;
		case 3: bad.fault = 1; break;
		case 4: bad.gauge_flags = 0xc000; break;
		case 5: bad.cell1_uv = 4600001; break;
		case 6: bad.cell2_uv = 1900000; break;
		case 7: bad.pack_uv = 8200000; break;
		case 8: bad.temp_decic = 530; break;
		default: bad.temp_decic = -21; break;
		}
		int error = sm_policy(&bad, 4362500, 250000, 900000, &target);
		CHECK(error);
		CHECK(!sm_cycle_full_allowed(1, 0, error));
		sm_cycle_init(&c, NS(1));
		sm_cycle_update(&c, NS(1), 1, 0);
		CHECK(sm_cycle_update(&c, NS(11), 1,
			sm_cycle_full_allowed(1, 0, error)) == 10);
	}
	printf("{\"cycle_cases\":%u,\"passed\":true}\n", cases);
	return 0;
}
