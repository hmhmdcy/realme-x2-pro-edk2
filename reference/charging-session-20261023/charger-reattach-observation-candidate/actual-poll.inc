static void sm_poll(struct work_struct *work)
{
	struct sm_charger *c = container_of(to_delayed_work(work),
					 struct sm_charger, work);
	bool notify = false;

	mutex_lock(&c->lock);
	if (c->paused) goto out;
	sm_step_locked(c);
	notify = sm_notification_locked(c);
	schedule_delayed_work(&c->work, msecs_to_jiffies(
		sm_reattach_delay_ms(&c->reattach, ktime_get_boottime_ns())));
out:
	mutex_unlock(&c->lock);
	if (notify)
		power_supply_changed(c->psy);
}
