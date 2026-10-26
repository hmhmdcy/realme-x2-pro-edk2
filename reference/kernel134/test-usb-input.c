/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include "samurai-usb-input-decode.h"
#include "actual-usb-read-functions.c"

static const struct samurai_usb_status live = { 1, 4, 0x10, 8, 0x23, 0x2b, 6 };
static int scenarios;

static void expect(struct samurai_usb_status s, int error, int online,
                   enum samurai_usb_kind kind, int current)
{
	struct samurai_usb_budget b = { -9, SAMURAI_USB_UNKNOWN, -9 };
	int ret = samurai_usb_decode(&s, &b);
	assert(ret == error);
	if (!ret)
		assert(b.online == online && b.kind == kind && b.current_ua == current);
	scenarios++;
}

int main(void)
{
	struct samurai_usb_status s;
	struct samurai_usb_budget b;
	struct samurai_usb_input input = { 0 };
	int ret, i;

	expect(live, 0, 1, SAMURAI_USB_CDP, 1500000);
	s = (struct samurai_usb_status){ 0 };
	expect(s, 0, 0, SAMURAI_USB_UNKNOWN, 0);
	for (i = 0; i < 4; i++) {
		s = live;
		if (i == 0) s.plugin = 0;
		if (i == 1) s.misc &= ~0x20;
		if (i == 2) s.misc &= ~1;
		if (i == 3) s.attached &= ~0x20;
		expect(s, -ENODATA, 0, SAMURAI_USB_UNKNOWN, -ENODATA);
	}
	for (i = 0; i < 3; i++) {
		s = live; s.misc |= (unsigned char[]){ 0x80, 0x40, 0x10 }[i];
		expect(s, -ENODATA, 0, SAMURAI_USB_UNKNOWN, -ENODATA);
	}
	s = live; s.misc &= ~8;
	expect(s, -ENODATA, 0, SAMURAI_USB_UNKNOWN, -ENODATA);
	s = live; s.legacy |= 1;
	expect(s, -ENODATA, 0, SAMURAI_USB_UNKNOWN, -ENODATA);
	for (i = 0; i < 5; i++) {
		s = live; s.plugin |= (unsigned char[]){ 1, 2, 4, 8, 0x20 }[i];
		expect(s, -ENODATA, 0, SAMURAI_USB_UNKNOWN, -ENODATA);
	}
	for (i = 0; i < 128; i++) {
		if (i == 8 || i == 4 || i == 2) continue;
		s = live; s.cc = i;
		expect(s, -ENODATA, 0, SAMURAI_USB_UNKNOWN, -ENODATA);
	}
	s = live; s.apsd = 0;
	expect(s, 0, 1, SAMURAI_USB_UNKNOWN, -ENODATA);
	s = live; s.result = 1;
	expect(s, 0, 1, SAMURAI_USB_SDP, -ENODATA);
	s = live; s.result = 8;
	expect(s, 0, 1, SAMURAI_USB_DCP, 1500000);
	for (i = 0; i < 128; i++) {
		if (i == 1 || i == 4 || i == 8) continue;
		s = live; s.result = i;
		expect(s, 0, 1, SAMURAI_USB_UNKNOWN, -ENODATA);
	}
	s = live; s.apsd |= 2;
	expect(s, 0, 1, SAMURAI_USB_UNKNOWN, -ENODATA);
	s = live; s.legacy = 0; s.cc = 4; s.apsd = 0; s.result = 0;
	expect(s, 0, 1, SAMURAI_USB_TYPE_C, 1500000);
	s.cc = 2;
	expect(s, 0, 1, SAMURAI_USB_TYPE_C, 3000000);
	s.legacy = 2;
	expect(s, 0, 1, SAMURAI_USB_UNKNOWN, -ENODATA);
	/* Execute the extracted production register reads, not a rewritten reader. */
	for (i = 0; i < 14; i++) {
		fixture_reset(live, live, i);
		b = (struct samurai_usb_budget){ -9, SAMURAI_USB_UNKNOWN, -9 };
		ret = samurai_usb_get_budget(&input, &b);
		assert(ret == -EIO && fixture_reads == i + 1 && b.online == -9);
		assert(fixture_lock_balance == 0);
		scenarios++;
	}
	s = (struct samurai_usb_status){ 0 };
	fixture_reset(live, s, -1);
	b = (struct samurai_usb_budget){ -9, SAMURAI_USB_UNKNOWN, -9 };
	assert(samurai_usb_get_budget(&input, &b) == -EAGAIN && b.online == -9);
	assert(fixture_reads == 14 && fixture_lock_balance == 0);
	scenarios++;
	fixture_reset(live, live, -1);
	assert(samurai_usb_get_budget(&input, &b) == 0);
	assert(b.online == 1 && b.current_ua == 1500000 && b.kind == SAMURAI_USB_CDP);
	assert(fixture_reads == 14 && fixture_lock_balance == 0);
	scenarios++;
	printf("K134_ACTUAL_C_DECODER_AND_IO_FAULT_SCENARIOS_PASS %d\n", scenarios);
	return 0;
}
