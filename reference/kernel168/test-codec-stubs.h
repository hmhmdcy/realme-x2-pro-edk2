/* SPDX-License-Identifier: GPL-2.0 */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdio.h>
typedef unsigned short u16;
typedef unsigned char u8;
typedef unsigned int u32;
#define BIT(n) (1U << (n))
#define GENMASK(h, l) (((~0U) << (l)) & ((~0U) >> (31 - (h))))
struct regmap { int unused; };
struct wcd934x_codec { struct regmap *regmap; void *dev; int version; };
struct snd_soc_component { void *dev; };
#define dev_err(...) ((void)0)
#define dev_info(...) ((void)0)
static struct wcd934x_codec codec;
static int io_call, fail_at, clk_users, fail_clock, version;
static void *dev_get_drvdata(void *dev) { (void)dev; return &codec; }
static int __wcd934x_cdc_mclk_enable(struct wcd934x_codec *c, bool on) {
    (void)c; if (on && fail_clock) return -EIO;
    clk_users += on ? 1 : -1; assert(clk_users >= 0); return 0;
}
static void usleep_range(int a, int b) { (void)a; (void)b; }
static int io(void) { return ++io_call == fail_at ? -EREMOTEIO : 0; }
static int regmap_update_bits(struct regmap *r, int reg, int mask, int val) {
    (void)r; (void)reg; (void)mask; (void)val; return io();
}
static int regmap_read(struct regmap *r, int reg, int *val) {
    (void)r; (void)reg; int ret = io(); if (!ret) *val = 1; return ret;
}
static int regmap_bulk_read(struct regmap *r, int reg, u8 *val, int size) {
    (void)r; (void)reg; (void)size; int ret = io(); if (!ret) *(u16 *)val = 1; return ret;
}
static int wcd934x_set_sido_input_src(struct wcd934x_codec *c, int src) {
    (void)c; (void)src; return io();
}
