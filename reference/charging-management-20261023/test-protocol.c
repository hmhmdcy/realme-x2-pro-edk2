/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "gauge-protocol.h"
#include "samurai-usb-input-decode.h"

int main(int argc, char **argv)
{
	unsigned char p[36], bad[36], command[2];
	int packets = 0, cases = 0, budget_cases = 0;
	FILE *f;

	assert(argc == 2);
	f = fopen(argv[1], "rb"); assert(f);
	while (fread(command, 1, 2, f) == 2) {
		unsigned int cmd = sm_le16(command);
		assert(fread(p, 1, 36, f) == 36);
		assert(!sm_mac_validate(p, 36, cmd));
		packets++; cases++;
		for (int n = 0; n < 36; n++)
			for (int bit = 0; bit < 8; bit++) {
				int used = n < p[35] - 2 || n >= 34;
				memcpy(bad, p, 36); bad[n] ^= 1 << bit;
				assert(used ? sm_mac_validate(bad, 36, cmd) < 0 :
				       !sm_mac_validate(bad, 36, cmd));
				cases++;
			}
		for (int n = 0; n < 36; n++) {
			assert(sm_mac_validate(p, n, cmd) == -EMSGSIZE); cases++;
		}
	}
	fclose(f);
	assert(packets == 6);
	assert(sm_mac_validate(p, 36, 0x1f) == -EINVAL); cases++;
	assert(!sm_gauge_protection_state(0x2719, 0, 0, 0x386, 0x18)); cases++;
	assert(sm_gauge_protection_state(0x2610, 0, 0, 0x386, 0x18) == -ENODEV); cases++;
	for (int bit = 0; bit < 32; bit++) {
		assert(sm_gauge_protection_state(0x2719, 1U << bit, 0, 0x386, 0x18) == -EIO);
		assert(sm_gauge_protection_state(0x2719, 0, 1U << bit, 0x386, 0x18) == -EIO);
		cases += 2;
	}
	for (unsigned int bit = 0; bit < 32; bit++) {
		unsigned int mask = (1U << 20) | (1U << 16) | 0x7c00;
		if (mask & (1U << bit)) {
			assert(sm_gauge_protection_state(0x2719, 0, 0, 0x386 | (1U << bit), 0x18) == -EACCES);
			cases++;
		}
	}
	assert(sm_gauge_protection_state(0x2719, 0, 0, 0x286, 0x18) == -EACCES); cases++;
	assert(sm_gauge_protection_state(0x2719, 0, 0, 0x386, 0x08) == -EACCES); cases++;
	assert(sm_gauge_protection_state(0x2719, 0, 0, 0x386, 0x1a) == -EACCES); cases++;
	/* Actual observed PM8150B: completed CDP, default Rp, legacy cable. */
	struct samurai_usb_status status = { 1, 4, 16, 8, 35, 41, 6 };
	struct samurai_usb_budget budget;
	assert(!samurai_usb_decode(&status, &budget));
	assert(budget.online && budget.kind == SAMURAI_USB_CDP && budget.current_ua == 1500000);
	assert(!samurai_usb_apply_udc(&budget, 1, 2000) && budget.current_ua == 1500000);
	budget_cases += 3;
	status.result = 1;
	for (int ua = -1000; ua <= 901000; ua += 1000) {
		assert(!samurai_usb_decode(&status, &budget));
		assert(budget.kind == SAMURAI_USB_SDP && budget.current_ua == -ENODATA);
		assert(!samurai_usb_apply_udc(&budget, 1, ua));
		assert(budget.current_ua == (ua < 0 || ua > 500000 ? -ENODATA : ua));
		budget_cases++;
	}
	assert(!samurai_usb_decode(&status, &budget));
	assert(!samurai_usb_apply_udc(&budget, 0, 500000) && budget.current_ua == -ENODATA);
	assert(!samurai_usb_apply_udc(&budget, 1, 2000) && budget.current_ua == 2000);
	memset(&status, 0, sizeof(status));
	assert(!samurai_usb_decode(&status, &budget));
	assert(!budget.online && budget.current_ua == 0);
	budget_cases += 4;
	printf("{\"captured_packets\":%d,\"protocol_protection_cases\":%d,\"usb_budget_cases\":%d,\"passed\":true}\n",
	       packets, cases, budget_cases);
	return 0;
}
