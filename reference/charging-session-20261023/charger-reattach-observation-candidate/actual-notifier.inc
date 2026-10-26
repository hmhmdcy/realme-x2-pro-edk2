static int sm_supply_changed(struct notifier_block *nb, unsigned long event, void *data)
{
	struct sm_charger *c = container_of(nb, struct sm_charger, supply_notifier);
	if (event == PSY_EVENT_PROP_CHANGED && (data == c->input || data == c->protection) &&
	    !READ_ONCE(c->paused)) mod_delayed_work(system_wq, &c->work, 0);
	return NOTIFY_DONE;
}
