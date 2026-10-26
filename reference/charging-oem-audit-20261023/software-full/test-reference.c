/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>

enum {
	BATTERY_STATUS__INVALID, BATTERY_STATUS__REMOVED, BATTERY_STATUS__LOW_TEMP,
	BATTERY_STATUS__HIGH_TEMP, BATTERY_STATUS__COLD_TEMP,
	BATTERY_STATUS__LITTLE_COLD_TEMP, BATTERY_STATUS__COOL_TEMP,
	BATTERY_STATUS__LITTLE_COOL_TEMP, BATTERY_STATUS__NORMAL,
	BATTERY_STATUS__WARM_TEMP,
};
enum { CHG_STOP_VOTER__FULL = 1 };
#define FULL_COUNTS_SW 5
#define FULL_COUNTS_HW 4
#define D_RECHGING_CNT 5
#define charger_xlog_printk(...) ((void)0)

struct limits {
	int temp_normal_vfloat_mv, temp_cold_vfloat_mv, temp_little_cold_vfloat_mv;
	int temp_cool_vfloat_mv, temp_little_cool_vfloat_mv, temp_warm_vfloat_mv;
	int cold_vfloat_sw_limit, little_cold_vfloat_sw_limit, cool_vfloat_sw_limit;
	int little_cool_vfloat_sw_limit, normal_vfloat_sw_limit, warm_vfloat_sw_limit;
	int non_standard_vfloat_sw_limit, short_c_bat_vfloat_sw_limit;
	int non_standard_vfloat_mv, short_c_bat_vfloat_mv;
	int normal_vterm_hw_inc, non_normal_vterm_hw_inc, iterm_ma, recharge_mv;
	int vfloat_over_counts;
};
struct oplus_chg_chip {
	struct limits limits;
	int charger_exist, tbatt_status, icharging, batt_volt, temperature;
	int sw_full_count, sw_full, authenticate, hmac, in_rechging;
	int batt_full, tbatt_when_full, total_time;
	int short_prohibit, short_disable_rechg, starts, stops;
};
static int oplus_short_c_batt_is_prohibit_chg(struct oplus_chg_chip *chip)
{ return chip->short_prohibit; }
static int oplus_short_c_batt_is_disable_rechg(struct oplus_chg_chip *chip)
{ return chip->short_disable_rechg; }
static void oplus_chg_voter_charging_start(struct oplus_chg_chip *chip, int voter)
{ assert(voter == CHG_STOP_VOTER__FULL); chip->starts++; }
static void oplus_chg_voter_charging_stop(struct oplus_chg_chip *chip, int voter)
{ assert(voter == CHG_STOP_VOTER__FULL); chip->stops++; }

struct gauge_stub { int suspended, current_pre; struct { int reg_ai; } cmd_addr; };
static struct gauge_stub gauge, *gauge_ic = &gauge;
static int raw_current_word;
#define atomic_read(p) (*(p))
#define dev_err(...) ((void)0)
static int oplus_vooc_get_allow_reading(void) { return 1; }
static int bq27541_read_i2c(int reg, int *value)
{ assert(reg == 0x0c); *value = raw_current_word; return 0; }

#include "reference-functions.c"

static struct oplus_chg_chip init(int band)
{
	return (struct oplus_chg_chip){
		.charger_exist = 1, .authenticate = 1, .hmac = 1,
		.tbatt_status = band, .temperature = 250,
		.limits = {
#include "reference-limits.inc"
		},
	};
}

static unsigned int cases;
static void result(const char *name, int expected, int actual)
{
	assert(expected == actual);
	printf("%s{\"name\":\"%s\",\"expected_trigger_sample\":%d,\"actual_trigger_sample\":%d}",
		cases ? ",\n" : "", name, expected, actual);
	cases++;
}
static int sw(int band, int mv, int raw_current_ma)
{
	struct oplus_chg_chip chip = init(band);
	chip.batt_volt = mv;
	chip.icharging = -raw_current_ma;
	for (int n = 1; n <= 16; n++)
		if (oplus_chg_check_sw_full(&chip)) return n;
	return 0;
}
static int hw(int band, int mv)
{
	struct oplus_chg_chip chip = init(band);
	chip.charger_exist = 0;
	assert(!oplus_chg_check_hw_full(&chip));
	chip.charger_exist = 1; chip.batt_volt = mv;
	for (int n = 1; n <= 8; n++)
		if (oplus_chg_check_hw_full(&chip)) return n;
	return 0;
}
static int recharge(int band, int mv, int disabled)
{
	struct oplus_chg_chip chip = init(band);
	chip.batt_volt = 5000;
	oplus_chg_check_rechg_status(&chip); /* Reset static consecutive counter. */
	chip.batt_volt = mv; chip.short_disable_rechg = disabled;
	for (int n = 1; n <= 9; n++) {
		oplus_chg_check_rechg_status(&chip);
		if (chip.starts) return n;
	}
	return 0;
}
int main(void)
{
	struct oplus_chg_chip chip;
	int n, trigger;
	printf("{\"vectors\":[\n");
	result("normal_sw_voltage_equal_no_full", 0, sw(BATTERY_STATUS__NORMAL, 4350, 110));
	result("normal_sw_110mA_inclusive", 6, sw(BATTERY_STATUS__NORMAL, 4351, 110));
	result("normal_sw_111mA_no_full", 0, sw(BATTERY_STATUS__NORMAL, 4351, 111));
	result("normal_sw_zero_current", 11, sw(BATTERY_STATUS__NORMAL, 4351, 0));
	result("normal_sw_discharging", 11, sw(BATTERY_STATUS__NORMAL, 4351, -1));
	result("cold_sw_limit_equal", 0, sw(BATTERY_STATUS__COLD_TEMP, 3930, 110));
	result("cold_sw_limit_above", 6, sw(BATTERY_STATUS__COLD_TEMP, 3931, 110));
	result("littlecold_sw_limit_above", 6, sw(BATTERY_STATUS__LITTLE_COLD_TEMP, 4351, 110));
	result("warm_sw_limit_equal", 0, sw(BATTERY_STATUS__WARM_TEMP, 4080, 110));
	result("warm_sw_limit_above", 6, sw(BATTERY_STATUS__WARM_TEMP, 4081, 110));
	chip = init(BATTERY_STATUS__NORMAL); chip.batt_volt = 4351; chip.icharging = 0;
	for (n = 0; n < 5; n++) assert(!oplus_chg_check_sw_full(&chip));
	chip.icharging = -110;
	result("sw_shared_counter_5_zero_then_110mA", 6, oplus_chg_check_sw_full(&chip) ? 6 : 0);
	chip = init(BATTERY_STATUS__NORMAL); chip.batt_volt = 4351; chip.icharging = -110;
	for (n = 0; n < 5; n++) assert(!oplus_chg_check_sw_full(&chip));
	chip.icharging = -111; assert(!oplus_chg_check_sw_full(&chip));
	chip.icharging = -110; trigger = 0;
	for (n = 7; n <= 12; n++) if (oplus_chg_check_sw_full(&chip)) { trigger = n; break; }
	result("sw_high_current_resets_streak", 12, trigger);
	result("normal_hw_below_limit", 0, hw(BATTERY_STATUS__NORMAL, 4417));
	result("normal_hw_at_limit", 4, hw(BATTERY_STATUS__NORMAL, 4418));
	result("cold_hw_at_limit", 4, hw(BATTERY_STATUS__COLD_TEMP, 3998));
	result("warm_hw_at_limit", 4, hw(BATTERY_STATUS__WARM_TEMP, 4148));
	result("normal_recharge_equal", 6, recharge(BATTERY_STATUS__NORMAL, 4300, 0));
	result("normal_recharge_above", 0, recharge(BATTERY_STATUS__NORMAL, 4301, 0));
	result("littlecold_recharge_equal", 6, recharge(BATTERY_STATUS__LITTLE_COLD_TEMP, 4200, 0));
	result("littlecold_recharge_above", 0, recharge(BATTERY_STATUS__LITTLE_COLD_TEMP, 4201, 0));
	result("cold_recharge_equal", 6, recharge(BATTERY_STATUS__COLD_TEMP, 3680, 0));
	result("cold_recharge_above", 0, recharge(BATTERY_STATUS__COLD_TEMP, 3681, 0));
	result("warm_recharge_equal", 6, recharge(BATTERY_STATUS__WARM_TEMP, 4030, 0));
	result("warm_recharge_above", 0, recharge(BATTERY_STATUS__WARM_TEMP, 4031, 0));
	result("short_c_disables_recharge", 0, recharge(BATTERY_STATUS__NORMAL, 4200, 1));
	chip = init(BATTERY_STATUS__NORMAL); chip.batt_volt = 4351;
	chip.total_time = 35999; chip.in_rechging = 1;
	oplus_chg_full_action(&chip);
	assert(chip.batt_full && !chip.total_time && !chip.in_rechging && chip.stops == 1);
	result("full_action_zeroes_cycle_time", 1, chip.stops);
	printf("\n],\"case_count\":%u,\"current_vectors\":[", cases);
	const int words[] = { 0, 1, 110, 111, 0xffff, 0xff92, 0x8000 };
	const int expected[] = { 0, -1, -110, -111, 1, 110, 32768 };
	gauge.cmd_addr.reg_ai = 0x0c;
	for (unsigned int i = 0; i < sizeof(words) / sizeof(words[0]); i++) {
		raw_current_word = words[i];
		int actual = bq27541_get_average_current();
		assert(actual == expected[i]);
		printf("%s{\"raw_word\":%d,\"oem_icharging_ma\":%d,\"gauge_current_ma\":%d}",
			i ? "," : "", words[i], actual, -actual);
	}
	printf("],\"current_case_count\":7,\"passed\":true}\n");
	return 0;
}
