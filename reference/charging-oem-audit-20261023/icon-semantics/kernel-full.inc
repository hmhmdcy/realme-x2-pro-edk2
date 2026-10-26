static bool bq27xxx_battery_is_full(struct bq27xxx_device_info *di, int flags)
{
	if (di->opts & BQ27XXX_O_ZERO)
		return (flags & BQ27000_FLAG_FC);
	else if (di->opts & BQ27Z561_O_BITS)
		return (flags & BQ27Z561_FLAG_FC);
	else
		return (flags & BQ27XXX_FLAG_FC);
}
