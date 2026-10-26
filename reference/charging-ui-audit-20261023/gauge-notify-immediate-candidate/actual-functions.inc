static bool bq27xxx_samurai_instant(struct bq27xxx_device_info *di)
{
	return samurai_instant_current && di->chip == BQ28Z610 &&
		of_machine_is_compatible("realme,samurai") &&
		of_device_is_compatible(di->dev->of_node, "ti,bq28z610");
}

static void bq27xxx_external_power_changed(struct power_supply *psy)
{
	struct bq27xxx_device_info *di = power_supply_get_drvdata(psy);

	/* Native instantaneous status needs no average-current settling delay.
	 * Other chips and opt-out profiles retain the original 0.5s wait.
	 */
	mod_delayed_work(system_percpu_wq, &di->work,
			 bq27xxx_samurai_instant(di) ? 0 : HZ / 2);
}
