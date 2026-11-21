
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#include "bq27xxx-status-policy.h"

#define EXPORT_SYMBOL_GPL(symbol)
#define HZ 100
#define BQ27XXX_MANUFACTURER "test-bq"
#define time_is_before_jiffies(a) false

typedef uint32_t u32;

enum power_supply_property {
	POWER_SUPPLY_PROP_PRESENT = 0,
	POWER_SUPPLY_PROP_STATUS,
	POWER_SUPPLY_PROP_VOLTAGE_NOW,
	POWER_SUPPLY_PROP_CURRENT_NOW,
	POWER_SUPPLY_PROP_CURRENT_AVG,
	POWER_SUPPLY_PROP_CAPACITY,
	POWER_SUPPLY_PROP_MANUFACTURER,
};

enum {
	POWER_SUPPLY_STATUS_UNKNOWN = 0,
	POWER_SUPPLY_STATUS_CHARGING,
	POWER_SUPPLY_STATUS_DISCHARGING,
	POWER_SUPPLY_STATUS_NOT_CHARGING,
	POWER_SUPPLY_STATUS_FULL,
};

union power_supply_propval {
	int intval;
	const char *strval;
};

struct mutex { int unused; };
struct work_struct { int unused; };
struct delayed_work { struct work_struct work; };
struct power_supply;

struct power_supply_desc {
	int (*get_property)(struct power_supply *psy,
			    enum power_supply_property psp,
			    union power_supply_propval *val);
};

struct power_supply {
	struct power_supply_desc *desc;
};

struct bq27xxx_reg_cache {
	int flags;
	int capacity;
};

struct bq27xxx_device_info {
	bool removed;
	bool suspended;
	unsigned long last_update;
	union power_supply_propval last_status;
	struct delayed_work full_status_work;
	struct power_supply *bat;
	struct mutex lock;
	struct bq27xxx_reg_cache cache;
	unsigned long full_status_deadline;
	u32 full_status_generation;
	bool full_status_override;
};

static unsigned long jiffies = 1000;
static struct bq27xxx_device_info *active_di;
static int lock_depth;
static int raw_calls;
static int raw_values[4];
static int raw_results[4];
static bool revoke_on_first;

static void *power_supply_get_drvdata(struct power_supply *psy)
{
	(void)psy;
	return active_di;
}

static void mutex_lock(struct mutex *lock)
{
	(void)lock;
	lock_depth++;
}

static void mutex_unlock(struct mutex *lock)
{
	(void)lock;
	if (--lock_depth < 0) {
		fprintf(stderr, "mutex unlock underflow\n");
		_exit(1);
	}
}

static void bq27xxx_battery_update_unlocked(struct bq27xxx_device_info *di)
{
	(void)di;
}

static int bq27xxx_battery_current_and_status(
	struct bq27xxx_device_info *di,
	union power_supply_propval *val_curr,
	union power_supply_propval *val_status,
	void *cache)
{
	int index = raw_calls++;
	int result = index < 4 ? raw_results[index] : -EIO;
	int value = index < 4 ? raw_values[index] : 0;

	(void)di;
	(void)cache;
	if (val_curr)
		val_curr->intval = 0;
	if (val_status)
		val_status->intval = value;
	if (index == 0 && revoke_on_first) {
		active_di->full_status_override = false;
		active_di->full_status_deadline = 0;
		active_di->full_status_generation++;
	}
	return result;
}

static int bq27xxx_battery_voltage(struct bq27xxx_device_info *di,
				   union power_supply_propval *val)
{
	(void)di;
	val->intval = 0;
	return 0;
}

static int bq27xxx_samurai_average_current(
	struct bq27xxx_device_info *di,
	union power_supply_propval *val)
{
	(void)di;
	val->intval = 0;
	return 0;
}

static int bq27xxx_battery_get_property(struct power_supply *psy,
					enum power_supply_property psp,
					union power_supply_propval *val)
{
	int ret = 0;
	bool force_full;
	u32 force_full_generation;
	struct bq27xxx_device_info *di = power_supply_get_drvdata(psy);

	mutex_lock(&di->lock);
	if (time_is_before_jiffies(di->last_update + 5 * HZ))
		bq27xxx_battery_update_unlocked(di);
	force_full = bq27xxx_full_status_active(di->full_status_override,
			di->full_status_deadline, jiffies);
	force_full_generation = di->full_status_generation;
	mutex_unlock(&di->lock);

	if (psp != POWER_SUPPLY_PROP_PRESENT && di->cache.flags < 0)
		return di->cache.flags;

	switch (psp) {
	case POWER_SUPPLY_PROP_STATUS:
		ret = bq27xxx_battery_current_and_status(di, NULL, val, NULL);
		if (!ret && force_full &&
		    val->intval != POWER_SUPPLY_STATUS_CHARGING) {
			union power_supply_propval fresh;

			mutex_lock(&di->lock);
			if (bq27xxx_full_status_confirmed(
				    di->full_status_override,
				    di->full_status_deadline, jiffies,
				    di->full_status_generation,
				    force_full_generation)) {
				ret = bq27xxx_battery_current_and_status(
					di, NULL, &fresh, NULL);
				if (!ret)
					val->intval = bq27xxx_full_status_apply(
						fresh.intval, true,
						POWER_SUPPLY_STATUS_CHARGING,
						POWER_SUPPLY_STATUS_FULL);
			}
			mutex_unlock(&di->lock);
		}
		break;
	case POWER_SUPPLY_PROP_VOLTAGE_NOW:
		ret = bq27xxx_battery_voltage(di, val);
		break;
	case POWER_SUPPLY_PROP_PRESENT:
		val->intval = di->cache.flags < 0 ? 0 : 1;
		break;
	case POWER_SUPPLY_PROP_CURRENT_NOW:
		ret = bq27xxx_battery_current_and_status(di, val, NULL, NULL);
		break;
	case POWER_SUPPLY_PROP_CURRENT_AVG:
		ret = bq27xxx_samurai_average_current(di, val);
		break;
	case POWER_SUPPLY_PROP_CAPACITY:
		ret = bq27xxx_simple_value(di->cache.capacity, val);
		break;
	case POWER_SUPPLY_PROP_CAPACITY_LEVEL:
		ret = bq27xxx_battery_capacity_level(di, val);
		break;
	case POWER_SUPPLY_PROP_TEMP:
		ret = bq27xxx_battery_read_temperature(di, val);
		break;
	case POWER_SUPPLY_PROP_TIME_TO_EMPTY_NOW:
		ret = bq27xxx_battery_read_time(di, BQ27XXX_REG_TTE, val);
		break;
	case POWER_SUPPLY_PROP_TIME_TO_EMPTY_AVG:
		ret = bq27xxx_battery_read_time(di, BQ27XXX_REG_TTECP, val);
		break;
	case POWER_SUPPLY_PROP_TIME_TO_FULL_NOW:
		ret = bq27xxx_battery_read_time(di, BQ27XXX_REG_TTF, val);
		break;
	case POWER_SUPPLY_PROP_TECHNOLOGY:
		if (di->opts & BQ27XXX_O_MUL_CHEM)
			val->intval = POWER_SUPPLY_TECHNOLOGY_UNKNOWN;
		else
			val->intval = POWER_SUPPLY_TECHNOLOGY_LION;
		break;
	case POWER_SUPPLY_PROP_CHARGE_NOW:
		if (di->regs[BQ27XXX_REG_NAC] != INVALID_REG_ADDR)
			ret = bq27xxx_battery_read_nac(di, val);
		else
			ret = bq27xxx_battery_read_rc(di, val);
		break;
	case POWER_SUPPLY_PROP_CHARGE_FULL:
		ret = bq27xxx_battery_read_fcc(di, val);
		break;
	case POWER_SUPPLY_PROP_CHARGE_FULL_DESIGN:
		ret = bq27xxx_battery_read_dcap(di, val);
		break;
	/*
	 * TODO: Implement these to make registers set from
	 * power_supply_battery_info visible in sysfs.
	 */
	case POWER_SUPPLY_PROP_ENERGY_FULL_DESIGN:
		return -EINVAL;
	case POWER_SUPPLY_PROP_VOLTAGE_MIN_DESIGN:
		ret = bq27xxx_battery_read_dmin_volt(di, val);
		break;
	case POWER_SUPPLY_PROP_VOLTAGE_MAX_DESIGN:
		ret = bq27xxx_battery_read_dmax_volt(di, val);
		break;
	case POWER_SUPPLY_PROP_CYCLE_COUNT:
		ret = bq27xxx_battery_read_cyct(di, val);
		break;
	case POWER_SUPPLY_PROP_ENERGY_NOW:
		ret = bq27xxx_battery_read_energy(di, val);
		break;
	case POWER_SUPPLY_PROP_POWER_AVG:
		ret = bq27xxx_battery_pwr_avg(di, val);
		break;
	case POWER_SUPPLY_PROP_HEALTH:
		ret = bq27xxx_battery_read_health(di, val);
		break;
	case POWER_SUPPLY_PROP_MANUFACTURER:
		val->strval = BQ27XXX_MANUFACTURER;
		break;
	default:
		return -EINVAL;
	}

	return ret;
}

#define CHECK(condition) do { \
	if (!(condition)) { \
		fprintf(stderr, "%s:%d: check failed: %s\n", \
			__FILE__, __LINE__, #condition); \
		return 1; \
	} \
} while (0)

static void reset_state(struct bq27xxx_device_info *di,
			struct power_supply *bat)
{
	memset(di, 0, sizeof(*di));
	di->bat = bat;
	di->last_update = jiffies;
	di->full_status_override = true;
	di->full_status_deadline = jiffies + 4;
	di->full_status_generation = 7;
	di->cache.flags = 0;
	active_di = di;
	lock_depth = 0;
	raw_calls = 0;
	memset(raw_values, 0, sizeof(raw_values));
	memset(raw_results, 0, sizeof(raw_results));
	revoke_on_first = false;
}

int main(void)
{
	struct bq27xxx_device_info di;
	struct power_supply_desc desc = {0};
	struct power_supply bat = { .desc = &desc };
	union power_supply_propval value;

	reset_state(&di, &bat);
	raw_values[0] = POWER_SUPPLY_STATUS_DISCHARGING;
	raw_values[1] = POWER_SUPPLY_STATUS_CHARGING;
	CHECK(bq27xxx_battery_get_property(&bat, POWER_SUPPLY_PROP_STATUS,
					   &value) == 0);
	CHECK(value.intval == POWER_SUPPLY_STATUS_CHARGING);
	CHECK(raw_calls == 2 && lock_depth == 0);

	reset_state(&di, &bat);
	raw_values[0] = POWER_SUPPLY_STATUS_DISCHARGING;
	raw_values[1] = POWER_SUPPLY_STATUS_DISCHARGING;
	CHECK(bq27xxx_battery_get_property(&bat, POWER_SUPPLY_PROP_STATUS,
					   &value) == 0);
	CHECK(value.intval == POWER_SUPPLY_STATUS_FULL);
	CHECK(raw_calls == 2 && lock_depth == 0);

	reset_state(&di, &bat);
	raw_values[0] = POWER_SUPPLY_STATUS_CHARGING;
	CHECK(bq27xxx_battery_get_property(&bat, POWER_SUPPLY_PROP_STATUS,
					   &value) == 0);
	CHECK(value.intval == POWER_SUPPLY_STATUS_CHARGING);
	CHECK(raw_calls == 1 && lock_depth == 0);

	reset_state(&di, &bat);
	raw_values[0] = POWER_SUPPLY_STATUS_DISCHARGING;
	revoke_on_first = true;
	CHECK(bq27xxx_battery_get_property(&bat, POWER_SUPPLY_PROP_STATUS,
					   &value) == 0);
	CHECK(value.intval == POWER_SUPPLY_STATUS_DISCHARGING);
	CHECK(raw_calls == 1 && lock_depth == 0);

	reset_state(&di, &bat);
	raw_values[0] = POWER_SUPPLY_STATUS_DISCHARGING;
	raw_results[1] = -EIO;
	CHECK(bq27xxx_battery_get_property(&bat, POWER_SUPPLY_PROP_STATUS,
					   &value) == -EIO);
	CHECK(raw_calls == 2 && lock_depth == 0);

	reset_state(&di, &bat);
	di.cache.flags = -ENODEV;
	CHECK(bq27xxx_battery_get_property(&bat, POWER_SUPPLY_PROP_STATUS,
					   &value) == -ENODEV);
	CHECK(raw_calls == 0 && lock_depth == 0);

	return 0;
}
