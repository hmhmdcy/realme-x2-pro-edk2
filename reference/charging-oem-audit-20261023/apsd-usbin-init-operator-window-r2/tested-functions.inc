static unsigned long long ui_now(void) { return ktime_to_ms(ktime_get_boottime()); }

static unsigned long long ui_clock(void *ctx) { return ui_now(); }

static int ui_snapshot_read(void *ctx, struct ui_snapshot *s)
{
	struct ui_device *d = ctx;
	static const unsigned int regs[] = { 0x1307,0x1308,0x1310,0x1506,0x1509,0x150b,0x150d };
	unsigned int value, i;
	int ret;
	for (i = 0; i < ARRAY_SIZE(regs); i++) {
		ret = regmap_read(d->map, regs[i], &value);
		if (ret) return ret;
		s->raw[i] = value;
	}
	ret = regmap_read(d->map, UI_CFG, &value);
	if (!ret) s->cfg = value;
	return ret;
}

static int ui_config_read(void *ctx, unsigned int *value)
{ return regmap_read(((struct ui_device *)ctx)->map, UI_CFG, value); }

static int ui_bit_write(void *ctx, unsigned int value)
{
	if (value & ~UI_BIT) return -EINVAL;
	return regmap_update_bits(((struct ui_device *)ctx)->map, UI_CFG, UI_BIT, value);
}

static bool ui_drop_if_safe(struct ui_device *d)
{
	if (d->held_ref && !d->state.running && !d->state.pending_restore) {
		d->held_ref = false; return true;
	}
	return false;
}

static void ui_work(struct work_struct *work)
{
	struct ui_device *d = container_of(to_delayed_work(work), struct ui_device, work);
	bool put;
	mutex_lock(&d->lock);
	if (!d->paused && d->state.running) ui_step(&d->state, &d->io, ui_now());
	if (!d->paused && d->state.running)
		schedule_delayed_work(&d->work, msecs_to_jiffies(UI_POLL_MS));
	put = ui_drop_if_safe(d);
	mutex_unlock(&d->lock);
	if (put) module_put(THIS_MODULE);
}

static const char *ui_phase_name(enum ui_phase phase)
{
	static const char * const names[] = { "observed","waiting","clear_verified","restored","committed","timeout","error","cancelled" };
	return names[phase];
}

static const char *ui_bool(int value) { return value ? "true" : "false"; }

static ssize_t state_show(struct device *dev, struct device_attribute *attr, char *buf)
{
	struct ui_device *d = dev_get_drvdata(dev);
	struct ui_state *s = &d->state;
	u64 now = ui_now();
	ssize_t n;
	mutex_lock(&d->lock);
	n = sysfs_emit(buf, "{\"schema\":1,\"instance\":\"%016llx\",\"phase\":\"%s\",\"op\":%d,"
		"\"armed\":%s,\"running\":%s,\"held_ref\":%s,\"can_unload\":%s,"
		"\"pending_restore\":%s,\"commit_allowed\":%s,\"committed\":%s,"
		"\"old_valid\":%s,\"old_bit\":%d,\"before_cfg\":%u,\"after_cfg\":%u,"
		"\"write_attempted\":%s,\"write_return\":%d,\"readback_error\":%d,\"post_error\":%d,"
		"\"unknown_write\":%s,\"changed\":%s,\"error\":%d,\"clear_error\":%d,\"clear_write_return\":%d,"
		"\"off_samples\":%u,\"have_first\":%s,\"first_boottime_ms\":%llu,"
		"\"pre_started_boottime_ms\":%llu,\"prewrite_boottime_ms\":%llu,\"post_boottime_ms\":%llu,"
		"\"started_boottime_ms\":%llu,\"deadline_boottime_ms\":%llu,\"now_boottime_ms\":%llu,\"remaining_ms\":%llu,"
		"\"first\":[%u,%u,%u,%u,%u,%u,%u,%u],\"pre\":[%u,%u,%u,%u,%u,%u,%u,%u],"
		"\"post\":[%u,%u,%u,%u,%u,%u,%u,%u],\"saved\":[%u,%u,%u,%u,%u,%u,%u,%u]}\n",
		d->instance, ui_phase_name(s->phase), s->op, ui_bool(s->clear_used),ui_bool(s->running),ui_bool(d->held_ref),
		ui_bool(!s->running&&!s->pending_restore&&!d->held_ref),ui_bool(s->pending_restore),ui_bool(s->commit_allowed),ui_bool(s->committed),
		ui_bool(s->old_valid),s->old_bit,s->before_cfg,s->after_cfg,ui_bool(s->write_attempted),s->write_return,s->readback_error,s->post_error,
		ui_bool(s->unknown_write),ui_bool(s->changed),s->error,s->clear_error,s->clear_write_return,s->off_samples,ui_bool(s->have_first),s->first_ms,
		s->pre_started_ms,s->prewrite_ms,s->post_ms,
		s->started_ms,s->deadline_ms,now,(s->running&&now<s->deadline_ms)?s->deadline_ms-now:0ULL,
		s->first.raw[0],s->first.raw[1],s->first.raw[2],s->first.raw[3],s->first.raw[4],s->first.raw[5],s->first.raw[6],s->first.cfg,
		s->pre.raw[0],s->pre.raw[1],s->pre.raw[2],s->pre.raw[3],s->pre.raw[4],s->pre.raw[5],s->pre.raw[6],s->pre.cfg,
		s->post.raw[0],s->post.raw[1],s->post.raw[2],s->post.raw[3],s->post.raw[4],s->post.raw[5],s->post.raw[6],s->post.cfg,
		s->saved.raw[0],s->saved.raw[1],s->saved.raw[2],s->saved.raw[3],s->saved.raw[4],s->saved.raw[5],s->saved.raw[6],s->saved.cfg);
	mutex_unlock(&d->lock);
	return n;
}

static ssize_t control_store(struct device *dev, struct device_attribute *attr, const char *buf, size_t count)
{
	struct ui_device *d = dev_get_drvdata(dev);
	bool put = false, cancel = false;
	int ret = 0;
	mutex_lock(&d->lock);
	if (d->paused || d->joining) { ret = -EBUSY; goto unlock; }
	if (sysfs_streq(buf,"arm") || sysfs_streq(buf,"restore_saved")) {
		if (!d->held_ref) {
			if (!try_module_get(THIS_MODULE)) { ret = -ENODEV; goto unlock; }
			d->held_ref = true;
		}
		ret = ui_start(&d->state,sysfs_streq(buf,"arm")?UI_CLEAR:UI_RESTORE,ui_now());
		if (!ret) schedule_delayed_work(&d->work,0);
		else put = ui_drop_if_safe(d);
	} else if (sysfs_streq(buf,"commit")) {
		ret = ui_commit(&d->state); if (!ret) put = ui_drop_if_safe(d);
	} else if (sysfs_streq(buf,"cancel")) {
		if (!d->state.running) ret = -EALREADY;
		else { ui_terminal(&d->state,UI_CANCELLED,-ECANCELED);d->joining = true;cancel = true; }
	} else if (sysfs_streq(buf,"observe")) {
		if (d->state.running || d->state.pending_restore) ret = -EBUSY;
		else {
			ret = ui_snapshot_read(d,&d->state.post);
			d->state.phase = ret?UI_ERROR:UI_OBSERVED;d->state.error = ret;
		}
	} else ret = -EINVAL;
unlock:
	mutex_unlock(&d->lock);
	/* Never hold the mutex while joining work. Work itself rechecks running. */
	if (cancel) {
		cancel_delayed_work_sync(&d->work);
		mutex_lock(&d->lock);d->joining = false;put = ui_drop_if_safe(d);mutex_unlock(&d->lock);
	}
	if (put) module_put(THIS_MODULE);
	if (ret) return ret;
	return count;
}

static void ui_stop(void *data)
{
	struct ui_device *d = data;
	bool put;
	mutex_lock(&d->lock);d->paused = true;
	if (d->state.running) ui_terminal(&d->state,UI_CANCELLED,-ECANCELED);
	mutex_unlock(&d->lock);
	cancel_delayed_work_sync(&d->work);
	mutex_lock(&d->lock);put = ui_drop_if_safe(d);mutex_unlock(&d->lock);
	if (put) module_put(THIS_MODULE);
}
