/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <strings.h>
#include <math.h>
#include <errno.h>

#define BIT(n) (1U << (n))
#define dev_err(...) ((void)0)
#define dev_dbg(...) ((void)0)
typedef int16_t s16;
enum { BQ27XXX_REG_AI, BQ27XXX_REG_FLAGS };
enum { POWER_SUPPLY_STATUS_UNKNOWN, POWER_SUPPLY_STATUS_CHARGING,
	POWER_SUPPLY_STATUS_DISCHARGING, POWER_SUPPLY_STATUS_NOT_CHARGING,
	POWER_SUPPLY_STATUS_FULL };
union power_supply_propval { int intval; };
struct bq27xxx_device_info { unsigned int opts; };
struct bq27xxx_reg_cache { int flags; };
static int raw_ai, raw_flags;
static int bq27xxx_read(struct bq27xxx_device_info *di, int reg, bool single)
{
	(void)di; assert(!single);
	assert(reg == BQ27XXX_REG_AI || reg == BQ27XXX_REG_FLAGS);
	return reg == BQ27XXX_REG_AI ? raw_ai : raw_flags;
}
#include "kernel-macros.inc"
#include "kernel-full.inc"
#include "kernel-status.inc"

typedef enum { UP_DEVICE_STATE_UNKNOWN, UP_DEVICE_STATE_CHARGING,
	UP_DEVICE_STATE_DISCHARGING, UP_DEVICE_STATE_EMPTY, UP_DEVICE_STATE_FULLY_CHARGED,
	UP_DEVICE_STATE_PENDING_CHARGE } UpDeviceState;
typedef char gchar;
typedef int gboolean;
struct native { const char *status; double current; };
typedef struct native GUdevDevice;
static char *g_strdup(const char *s)
{
	char *out = malloc(strlen(s) + 1); assert(out);
	strcpy(out, s); return out;
}
static char *g_strdup_printf(const char *fmt, ...)
{
	char out[256]; va_list args;
	va_start(args, fmt); int n = vsnprintf(out, sizeof(out), fmt, args); va_end(args);
	assert(n >= 0 && n < (int)sizeof(out)); return g_strdup(out);
}
#define g_free free
#define g_ascii_strcasecmp strcasecmp
#define g_warning(...) ((void)0)
static char *up_device_supply_get_string(GUdevDevice *native, const char *key)
{ assert(!strcmp(key, "status")); return g_strdup(native->status); }
static double g_udev_device_get_sysfs_attr_as_double_uncached(GUdevDevice *native,
							    const char *key)
{ assert(!strcmp(key, "current_now")); return native->current; }
#include "upower-state.inc"
static UpDeviceState upower(GUdevDevice *native)
{
	struct { UpDeviceState state; } values;
#include "upower-override.inc"
	return values.state;
}
static char *icon(UpDeviceState state, double percentage)
{
	gboolean is_charging, is_charged;
	int smallest_ten;
	char *icon_name = NULL;
#include "phosh-icon.inc"
	return icon_name;
}
static const char *kernel_name(int status)
{
	switch (status) {
	case POWER_SUPPLY_STATUS_FULL: return "Full";
	case POWER_SUPPLY_STATUS_CHARGING: return "Charging";
	case POWER_SUPPLY_STATUS_DISCHARGING: return "Discharging";
	case POWER_SUPPLY_STATUS_NOT_CHARGING: return "Not charging";
	default: return "Unknown";
	}
}
static const char *up_name(UpDeviceState state)
{
	switch (state) {
	case UP_DEVICE_STATE_FULLY_CHARGED: return "FullyCharged";
	case UP_DEVICE_STATE_CHARGING: return "Charging";
	case UP_DEVICE_STATE_DISCHARGING: return "Discharging";
	case UP_DEVICE_STATE_PENDING_CHARGE: return "PendingCharge";
	default: return "Unknown";
	}
}
static unsigned int cases;
static void chain(const char *name, int fc, int ai_ma, int instant_ma,
		  int source_online, int source_budget_ua, int percentage,
		  int want_kernel, UpDeviceState want_up, const char *want_icon)
{
	struct bq27xxx_device_info di = { .opts = BQ27Z561_O_BITS };
	union power_supply_propval curr, status;
	raw_ai = (uint16_t)(int16_t)ai_ma;
	raw_flags = fc ? BQ27Z561_FLAG_FC : 0;
	assert(!bq27xxx_battery_current_and_status(&di, &curr, &status, NULL));
	assert(status.intval == want_kernel && curr.intval == ai_ma * 1000);
	GUdevDevice native = { .status = kernel_name(status.intval), .current = curr.intval };
	UpDeviceState us = upower(&native);
	assert(us == want_up);
	/* Synthetic handoff only: actual UPower DisplayDevice aggregation and
	 * Phosh drawing are not executed. Exercise Phosh's branch on that state. */
	char *selected = icon(us, percentage);
	assert(!strcmp(selected, want_icon));
	printf("%s{\"name\":\"%s\",\"source_online\":%d,\"source_budget_ua\":%d,"
		"\"fc\":%d,\"ai_ma\":%d,\"instantaneous_ma\":%d,\"kernel_status\":\"%s\","
		"\"upower_battery_state\":\"%s\",\"phosh_selected_icon\":\"%s\"}",
		cases ? ",\n" : "", name, source_online, source_budget_ua, fc, ai_ma,
		instant_ma, kernel_name(status.intval), up_name(us), selected);
	free(selected); cases++;
}
int main(void)
{
	printf("{\"vectors\":[\n");
	chain("FC_after_unplug_negative_AI", 1, -5, -200, 0, 0, 99,
		POWER_SUPPLY_STATUS_FULL, UP_DEVICE_STATE_FULLY_CHARGED, "battery-level-100-charged-symbolic");
	chain("FC_while_external_negative_AI", 1, -5, -5, 1, 100000, 99,
		POWER_SUPPLY_STATUS_FULL, UP_DEVICE_STATE_FULLY_CHARGED, "battery-level-100-charged-symbolic");
	chain("old_positive_AI_after_unplug", 0, 5, -200, 0, 0, 89,
		POWER_SUPPLY_STATUS_CHARGING, UP_DEVICE_STATE_CHARGING, "battery-level-80-charging-symbolic");
	chain("external_SDP100_negative_net_AI", 0, -4, -4, 1, 100000, 89,
		POWER_SUPPLY_STATUS_DISCHARGING, UP_DEVICE_STATE_DISCHARGING, "battery-level-80-symbolic");
	chain("zero_AI_external", 0, 0, 0, 1, 100000, 89,
		POWER_SUPPLY_STATUS_NOT_CHARGING, UP_DEVICE_STATE_PENDING_CHARGE, "battery-level-80-symbolic");
	chain("charging_at_100_selects_charged_icon", 0, 5, 5, 1, 500000, 100,
		POWER_SUPPLY_STATUS_CHARGING, UP_DEVICE_STATE_CHARGING, "battery-level-100-charged-symbolic");
	/* A separately read negative current overrides an advertised Charging,
	 * while an advertised Full deliberately wins over the negative reading. */
	GUdevDevice native = { .status = "Charging", .current = -4000 };
	assert(upower(&native) == UP_DEVICE_STATE_DISCHARGING);
	native.status = "Full";
	assert(upower(&native) == UP_DEVICE_STATE_FULLY_CHARGED);
	printf("\n],\"chain_cases\":%u,\"override_cases\":2,\"passed\":true}\n", cases);
	return 0;
}
