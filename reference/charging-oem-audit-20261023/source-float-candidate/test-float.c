#include <assert.h>
#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include "samurai-usb-input-decode.h"
static int checks;
#define CHECK(x) do { assert(x); checks++; } while (0)
static struct samurai_usb_status actual = { 0x21, 0x10, 0x10, 8, 0x23, 0x2b, 6 };
static struct samurai_usb_budget resolve(struct samurai_usb_status s, int valid, int ua) {
    struct samurai_usb_budget b;
    CHECK(!samurai_usb_decode(&s, &b));
    CHECK(!samurai_usb_apply_udc(&b, valid, ua));
    return b;
}
int main(void) {
    struct samurai_usb_budget b = resolve(actual, 1, 100000);
    CHECK(b.online && b.kind == SAMURAI_USB_SDP && b.current_ua == 100000);
    b = resolve(actual, 0, 500000);
    CHECK(b.kind == SAMURAI_USB_FLOAT && b.current_ua == -ENODATA);
    int limits[] = { INT_MIN, -110, -ETIMEDOUT, -1, 0, 2000, 100000, 500000, 500001, 900000, INT_MAX };
    for (unsigned i = 0; i < sizeof(limits)/sizeof(limits[0]); i++) {
        int ua = limits[i]; b = resolve(actual, 1, ua);
        CHECK(b.current_ua == (ua >= 0 && ua <= 500000 ? ua : -ENODATA));
        CHECK(b.kind == (ua >= 0 && ua <= 500000 ? SAMURAI_USB_SDP : SAMURAI_USB_FLOAT));
    }
    for (int ua = -1000; ua <= 901000; ua += 1000) {
        b = resolve(actual, 1, ua);
        CHECK(b.current_ua == (ua >= 0 && ua <= 500000 ? ua : -ENODATA));
    }
    for (int apsd = 0; apsd <= 255; apsd++) {
        struct samurai_usb_status s = actual; s.apsd = apsd;
        b = resolve(s, 1, 100000);
        int permitted = (apsd & 1) && !(apsd & 0x8e);
        CHECK(permitted ? b.kind == SAMURAI_USB_SDP && b.current_ua == 100000 :
                          b.current_ua == -ENODATA && b.kind == SAMURAI_USB_UNKNOWN);
    }
    for (int result = 0; result <= 255; result++) {
        struct samurai_usb_status s = actual; s.result = result;
        b = resolve(s, 1, 500000);
        if (result != 0x10 && (result & 0x7f) != 1 && (result & 0x7f) != 4 && (result & 0x7f) != 8)
            CHECK(b.current_ua == -ENODATA);
        if (result & 0x60) CHECK(b.current_ua == -ENODATA);
    }
    for (int cc = 0; cc < 128; cc++) {
        struct samurai_usb_status s = actual; s.cc = cc;
        int ret = samurai_usb_decode(&s, &b);
        if (cc == 2 || cc == 4 || cc == 8) {
            CHECK(ret == 0 && b.kind == SAMURAI_USB_FLOAT && b.current_ua == -ENODATA);
            CHECK(!samurai_usb_apply_udc(&b, 1, 100000) && b.current_ua == 100000);
        } else CHECK(ret == -ENODATA && b.current_ua == -ENODATA);
    }
    for (int cc = 2; cc <= 4; cc += 2) {
        struct samurai_usb_status s = actual; s.cc = cc; s.legacy = 0;
        b = resolve(s, 0, 500000);
        CHECK(b.kind == SAMURAI_USB_FLOAT && b.current_ua == -ENODATA);
        b = resolve(s, 1, 100000);
        CHECK(b.kind == SAMURAI_USB_SDP && b.current_ua == 100000);
    }
    for (int bit = 0; bit < 8; bit++) {
        if (0x2f & (1 << bit)) {
            struct samurai_usb_status s = actual; s.plugin |= 1 << bit;
            CHECK(samurai_usb_decode(&s, &b) == -ENODATA && b.current_ua == -ENODATA);
        }
        if (0xd0 & (1 << bit)) {
            struct samurai_usb_status s = actual; s.misc |= 1 << bit;
            CHECK(samurai_usb_decode(&s, &b) == -ENODATA && b.current_ua == -ENODATA);
        }
    }
    struct samurai_usb_status s = actual; s.legacy |= 1;
    CHECK(samurai_usb_decode(&s, &b) == -ENODATA);
    s = actual; s.misc &= ~8; CHECK(samurai_usb_decode(&s, &b) == -ENODATA);
    s = actual; s.attached = 0; CHECK(samurai_usb_decode(&s, &b) == -ENODATA);
    s = actual; s.plugin = 0; CHECK(samurai_usb_decode(&s, &b) == -ENODATA);
    s = (struct samurai_usb_status){0}; b = resolve(s, 1, 500000);
    CHECK(!b.online && b.current_ua == 0 && b.kind == SAMURAI_USB_UNKNOWN);
    /* Existing SDP/CDP/DCP/Rp semantics are unchanged for non-FLOAT result. */
    for (int ua = -1000; ua <= 901000; ua += 1000) {
        s = actual; s.result = 1; b = resolve(s, 1, ua);
        CHECK(b.kind == SAMURAI_USB_SDP && b.current_ua == (ua < 0 || ua > 500000 ? -ENODATA : ua));
        s.result = 4; b = resolve(s, 1, ua);
        CHECK(b.kind == SAMURAI_USB_CDP && b.current_ua == 1500000);
        s.result = 8; b = resolve(s, 1, ua);
        CHECK(b.kind == SAMURAI_USB_DCP && b.current_ua == 1500000);
    }
    s = actual; s.result = 0; s.legacy = 0; s.cc = 4;
    b = resolve(s, 1, 100000); CHECK(b.kind == SAMURAI_USB_TYPE_C && b.current_ua == 1500000);
    printf("{\"candidate_assertions\":%d,\"actual_float_100000_resolves_sdp\":true,\"hardware_accessed\":false}\n", checks);
    return 0;
}
