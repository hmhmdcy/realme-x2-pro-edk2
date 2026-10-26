/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef SAMURAI_USB_INPUT_DECODE_H
#define SAMURAI_USB_INPUT_DECODE_H

/* Status fields from the RMX1931 OEM SMB5 header and PM8150B Type-C driver. */
struct samurai_usb_status {
	unsigned char apsd, result, plugin, cc, attached, misc, legacy;
};

enum samurai_usb_kind {
	SAMURAI_USB_UNKNOWN, SAMURAI_USB_SDP, SAMURAI_USB_CDP,
	SAMURAI_USB_DCP, SAMURAI_USB_TYPE_C,
};

struct samurai_usb_budget {
	int online;
	enum samurai_usb_kind kind;
	int current_ua;
};

/* A detection result is an advertised allowance, never a current measurement.
 * SDP requires the UDC's configured/suspended budget, so leave it unavailable.
 * No PD contract, proprietary charging mode or ambiguous result is inferred.
 */
static inline int samurai_usb_decode(const struct samurai_usb_status *s,
				     struct samurai_usb_budget *b)
{
	unsigned int cc = s->cc & 0x7f;
	unsigned int result = s->result & 0x7f;
	int plugin = !!(s->plugin & 0x10);
	int vbus = !!(s->misc & 0x20);
	int attached = !!(s->misc & 1);
	int state_attached = !!(s->attached & 0x20);

	b->online = 0;
	b->kind = SAMURAI_USB_UNKNOWN;
	b->current_ua = -ENODATA;
	if (!plugin && !vbus && !attached && !state_attached) {
		b->current_ua = 0;
		return 0;
	}
	/* Transitional, source-role, water/error and noncompliant states fail. */
	if (!plugin || !vbus || !attached || !state_attached ||
	    (s->misc & 0xd0) || !(s->misc & 8) || (s->legacy & 1) ||
	    (s->plugin & 0x2f))
		return -ENODATA;
	if (cc != 8 && cc != 4 && cc != 2)
		return -ENODATA;
	b->online = 1;
	/* A completed QC detection is outside this observer's contract. */
	if ((s->apsd & 2) || (result & 0x60))
		return 0;
	if (!(s->legacy & 2) && (cc == 4 || cc == 2)) {
		b->kind = SAMURAI_USB_TYPE_C;
		b->current_ua = cc == 4 ? 1500000 : 3000000;
		return 0;
	}
	if (!(s->apsd & 1))
		return 0;
	switch (result) {
	case 1:
		b->kind = SAMURAI_USB_SDP;
		break;
	case 4:
		b->kind = SAMURAI_USB_CDP;
		b->current_ua = 1500000;
		break;
	case 8:
		b->kind = SAMURAI_USB_DCP;
		b->current_ua = 1500000;
		break;
	}
	return 0;
}

static inline int samurai_usb_status_equal(const struct samurai_usb_status *a,
					   const struct samurai_usb_status *b)
{
	return a->apsd == b->apsd && a->result == b->result &&
	       a->plugin == b->plugin && a->cc == b->cc &&
	       a->attached == b->attached && a->misc == b->misc &&
	       a->legacy == b->legacy;
}

#endif
