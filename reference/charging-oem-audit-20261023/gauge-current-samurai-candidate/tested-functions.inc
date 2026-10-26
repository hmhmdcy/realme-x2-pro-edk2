static inline int bq27xxx_read(struct bq27xxx_device_info *di, int reg_index,
			       bool single)
{
	int ret;

	if (!di || di->regs[reg_index] == INVALID_REG_ADDR)
		return -EINVAL;

	ret = di->bus.read(di, di->regs[reg_index], single);
	if (ret < 0)
		dev_dbg(di->dev, "failed to read register 0x%02x (index %d)\n",
			di->regs[reg_index], reg_index);

	return ret;
}

static bool bq27xxx_samurai_instant(struct bq27xxx_device_info *di)
{
	return samurai_instant_current && di->chip == BQ28Z610 &&
		of_machine_is_compatible("realme,samurai") &&
		of_device_is_compatible(di->dev->of_node, "ti,bq28z610");
}

static void bq27xxx_samurai_props(struct bq27xxx_device_info *di,
				 struct power_supply_desc *desc)
{
	if (!bq27xxx_samurai_instant(di))
		return;
	desc->properties = bq28z610_samurai_props;
	desc->num_properties = ARRAY_SIZE(bq28z610_samurai_props);
}

static int bq27xxx_samurai_average_current(struct bq27xxx_device_info *di,
					 union power_supply_propval *val)
{
	int raw;

	if (!bq27xxx_samurai_instant(di))
		return -EINVAL;
	raw = bq27xxx_read(di, BQ27XXX_REG_AI, false);
	if (raw < 0)
		return raw;
	val->intval = (int)((s16)raw) * 1000;
	return 0;
}

static bool bq27xxx_battery_is_full(struct bq27xxx_device_info *di, int flags)
{
	if (di->opts & BQ27XXX_O_ZERO)
		return (flags & BQ27000_FLAG_FC);
	else if (di->opts & BQ27Z561_O_BITS)
		return (flags & BQ27Z561_FLAG_FC);
	else
		return (flags & BQ27XXX_FLAG_FC);
}

static int bq27xxx_battery_current_and_status(
	struct bq27xxx_device_info *di,
	union power_supply_propval *val_curr,
	union power_supply_propval *val_status,
	struct bq27xxx_reg_cache *cache)
{
	bool single_flags = (di->opts & BQ27XXX_O_ZERO);
	int curr;
	int flags;

	/* The native opt-in changes both STATUS and CURRENT_NOW together.
	 * CURRENT_AVG retains the original signed 0x14 path. Do not consult
	 * any charger/source property while servicing a gauge property.
	 */
	if (bq27xxx_samurai_instant(di))
		curr = di->bus.read(di, 0x0c, false);
	else
		curr = bq27xxx_read(di, BQ27XXX_REG_AI, false);
	if (curr < 0) {
		dev_err(di->dev, "error reading current\n");
		return curr;
	}

	if (cache) {
		flags = cache->flags;
	} else {
		flags = bq27xxx_read(di, BQ27XXX_REG_FLAGS, single_flags);
		if (flags < 0) {
			dev_err(di->dev, "error reading flags\n");
			return flags;
		}
	}

	if (di->opts & BQ27XXX_O_ZERO) {
		if (!(flags & BQ27000_FLAG_CHGS)) {
			dev_dbg(di->dev, "negative current!\n");
			curr = -curr;
		}

		curr = curr * BQ27XXX_CURRENT_CONSTANT / BQ27XXX_RS;
	} else {
		/* Other gauges return signed value */
		curr = (int)((s16)curr) * 1000;
	}

	if (val_curr)
		val_curr->intval = curr;

	if (val_status) {
		if (bq27xxx_battery_is_full(di, flags))
			val_status->intval = POWER_SUPPLY_STATUS_FULL;
		else if (curr > 0)
			val_status->intval = POWER_SUPPLY_STATUS_CHARGING;
		else if (curr < 0)
			val_status->intval = POWER_SUPPLY_STATUS_DISCHARGING;
		else
			val_status->intval = POWER_SUPPLY_STATUS_NOT_CHARGING;
	}

	return 0;
}

static void bq27xxx_battery_update_unlocked(struct bq27xxx_device_info *di)
{
	union power_supply_propval status = di->last_status;
	struct bq27xxx_reg_cache cache = {0, };
	bool has_singe_flag = di->opts & BQ27XXX_O_ZERO;

	cache.flags = bq27xxx_read(di, BQ27XXX_REG_FLAGS, has_singe_flag);
	if (di->chip == BQ27000 && (cache.flags & 0xff) == 0xff)
		cache.flags = -ENODEV; /* bq27000 hdq read error */
	if (cache.flags >= 0) {
		cache.capacity = bq27xxx_battery_read_soc(di);

		/*
		 * On gauges with signed current reporting the current must be
		 * checked to detect charging <-> discharging status changes.
		 */
		if (!(di->opts & BQ27XXX_O_ZERO))
			bq27xxx_battery_current_and_status(di, NULL, &status, &cache);
	}

	if ((di->cache.capacity != cache.capacity) ||
	    (di->cache.flags != cache.flags) ||
	    (di->last_status.intval != status.intval)) {
		di->last_status.intval = status.intval;
		power_supply_changed(di->bat);
	}

	if (memcmp(&di->cache, &cache, sizeof(cache)) != 0)
		di->cache = cache;

	di->last_update = jiffies;

	if (!di->removed && poll_interval > 0)
		mod_delayed_work(system_percpu_wq, &di->work, poll_interval * HZ);
}

void bq27xxx_battery_update(struct bq27xxx_device_info *di)
{
	mutex_lock(&di->lock);
	bq27xxx_battery_update_unlocked(di);
	mutex_unlock(&di->lock);
}

static int bq27xxx_battery_get_property(struct power_supply *psy,
					enum power_supply_property psp,
					union power_supply_propval *val)
{
	int ret = 0;
	struct bq27xxx_device_info *di = power_supply_get_drvdata(psy);

	mutex_lock(&di->lock);
	if (time_is_before_jiffies(di->last_update + 5 * HZ))
		bq27xxx_battery_update_unlocked(di);
	mutex_unlock(&di->lock);

	if (psp != POWER_SUPPLY_PROP_PRESENT && di->cache.flags < 0)
		return di->cache.flags;

	switch (psp) {
	case POWER_SUPPLY_PROP_STATUS:
		ret = bq27xxx_battery_current_and_status(di, NULL, val, NULL);
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

static int original_current_and_status(
	struct bq27xxx_device_info *di,
	union power_supply_propval *val_curr,
	union power_supply_propval *val_status,
	struct bq27xxx_reg_cache *cache)
{
	bool single_flags = (di->opts & BQ27XXX_O_ZERO);
	int curr;
	int flags;

	curr = bq27xxx_read(di, BQ27XXX_REG_AI, false);
	if (curr < 0) {
		dev_err(di->dev, "error reading current\n");
		return curr;
	}

	if (cache) {
		flags = cache->flags;
	} else {
		flags = bq27xxx_read(di, BQ27XXX_REG_FLAGS, single_flags);
		if (flags < 0) {
			dev_err(di->dev, "error reading flags\n");
			return flags;
		}
	}

	if (di->opts & BQ27XXX_O_ZERO) {
		if (!(flags & BQ27000_FLAG_CHGS)) {
			dev_dbg(di->dev, "negative current!\n");
			curr = -curr;
		}

		curr = curr * BQ27XXX_CURRENT_CONSTANT / BQ27XXX_RS;
	} else {
		/* Other gauges return signed value */
		curr = (int)((s16)curr) * 1000;
	}

	if (val_curr)
		val_curr->intval = curr;

	if (val_status) {
		if (bq27xxx_battery_is_full(di, flags))
			val_status->intval = POWER_SUPPLY_STATUS_FULL;
		else if (curr > 0)
			val_status->intval = POWER_SUPPLY_STATUS_CHARGING;
		else if (curr < 0)
			val_status->intval = POWER_SUPPLY_STATUS_DISCHARGING;
		else
			val_status->intval = POWER_SUPPLY_STATUS_NOT_CHARGING;
	}

	return 0;
}
