static int bq27xxx_battery_current_and_status(
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
