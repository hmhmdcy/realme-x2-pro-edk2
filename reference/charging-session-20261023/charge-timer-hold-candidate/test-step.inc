int main(void)
{
	struct sm_charger c;
	struct bus bus;
	struct frame f;
	initialize(&c, &bus);
	CHECK(enabled(&bus));
	f = normal(); f.sample.gauge_flags = 0x4000;
	CHECK(at(&c, 35990, normal()) == 0 && c.sample.session_seconds == 35990);
	CHECK(at(&c, 35991, f) == -EAGAIN && stopped(&bus) && !c.latched);
#if BASELINE
	(void)sequences;
	/* Old actual step counts another twelve hours despite its successful stop. */
	CHECK(at(&c, 79191, f) == -ETIME && c.cycle.timed_out && c.latched);
	printf("{\"baseline_noncharging_timeout_reproduced\":true,\"assertions\":%u}\n", assertions);
#else
	sequences++;
	CHECK(c.timer_hold_confirmed);
	CHECK(at(&c, 79191, f) == -EAGAIN && !c.cycle.timed_out && !c.latched);
	CHECK(c.sample.session_seconds == 35991 && stopped(&bus));
	CHECK(at(&c, 79192, normal()) == 0 && enabled(&bus) && !c.timer_hold_confirmed);
	CHECK(c.sample.session_seconds == 35991);
	CHECK(at(&c, 79195, normal()) == 0 && c.sample.session_seconds == 35994);
	CHECK(at(&c, 79201, normal()) == -ETIME && c.cycle.timed_out && c.latched);
	f = normal(); f.full = true;
	CHECK(at(&c, 79202, f) == -ETIME && c.cycle.timed_out && c.latched);

	/* Operator stop pauses, never forgives the time already accumulated. */
	sequences++;
	initialize(&c, &bus); c.auto_requested = false;
	CHECK(at(&c, 10, normal()) == 0 && stopped(&bus) && c.timer_hold_confirmed);
	CHECK(at(&c, 43210, normal()) == 0 && c.sample.session_seconds == 10);
	c.auto_requested = true;
	CHECK(at(&c, 43211, normal()) == 0 && enabled(&bus) && c.sample.session_seconds == 10);
	CHECK(at(&c, 43213, normal()) == 0 && c.sample.session_seconds == 12);

	/* A fresh thermal hold uses the same confirmed-stop gate. */
	sequences++;
	initialize(&c, &bus);f = normal(); f.sample.temp_decic = 531;
	CHECK(at(&c, 10, f) == -ERANGE && !c.latched && c.timer_hold_confirmed && stopped(&bus));
	CHECK(at(&c, 43210, f) == -ERANGE && c.sample.session_seconds == 10 && !c.cycle.timed_out);
	CHECK(at(&c, 43211, normal()) == 0 && enabled(&bus) && !c.timer_hold_confirmed);

	/* Unknown/incomplete telemetry cannot exclude an interval. */
	sequences++;
	initialize(&c, &bus);c.auto_requested = false;
	CHECK(at(&c, 10, normal()) == 0 && c.timer_hold_confirmed);
	f = normal();f.sample.online = 0;f.sample.valid = 0;f.collect_error = -EREMOTEIO;
	CHECK(at(&c, 43210, f) == -EREMOTEIO && c.latched && c.cycle.timed_out && !c.timer_hold_confirmed);

	/* A failed hardware stop is not a valid pause, including after recovery. */
	sequences++;
	initialize(&c, &bus);bus.fail_stop_write = 1;
	f = normal();f.sample.gauge_flags = 0x4000;
	CHECK(at(&c, 10, f) == -EAGAIN && c.stop_error == -EREMOTEIO && c.latched && !c.timer_hold_confirmed);
	bus.fail_stop_write = 0;
	CHECK(at(&c, 43210, normal()) == -ETIME && c.cycle.timed_out && c.latched);

	/* Shadow mode never claims it stopped actual charging. */
	sequences++;
	initialize(&c, &bus);control = false;
	f = normal();f.sample.gauge_flags = 0x4000;
	CHECK(at(&c, 10, f) == -EAGAIN && !c.timer_hold_confirmed && enabled(&bus));
	CHECK(at(&c, 43210, f) == -ETIME && c.cycle.timed_out);
	control = true;

	/* Bad clocks still fail closed; genuine detach retains its old reset. */
	sequences++;
	initialize(&c, &bus);c.auto_requested = false;
	CHECK(at(&c, 10, normal()) == 0 && c.timer_hold_confirmed);
	CHECK(at(&c, 9, normal()) == -ETIME && c.cycle.timed_out);
	f = normal();f.sample.online = 0;
	CHECK(at(&c, 11, f) == 0 && !c.cycle.timed_out && !c.cycle.attached);
	CHECK(at(&c, 12, normal()) == 0 && c.sample.session_seconds == 0);

	/* Subsecond repeated calls retain nanosecond remainder and no overflow. */
	sequences++;
	{
		struct sm_charge_cycle timer;
		sm_cycle_init(&timer, 0);
		CHECK(sm_cycle_update(&timer, 0, 1, 0) == 0);
		CHECK(sm_cycle_update_held(&timer, 1750000000ULL, 1, 0, 0) == 1);
		for (unsigned int i = 1; i <= 20; i++)
			CHECK(sm_cycle_update_held(&timer, 1750000000ULL + i * 250000000ULL, 1, 0, 1) == 1);
		CHECK(sm_cycle_update_held(&timer, 7000000000ULL, 1, 0, 0) == 2);
		sm_cycle_init(&timer, UINT64_MAX - 100);
		CHECK(sm_cycle_update_held(&timer, UINT64_MAX - 100, 1, 0, 0) == 0);
		CHECK(sm_cycle_update_held(&timer, UINT64_MAX, 1, 0, 1) == 0);
		CHECK(timer.anchor_ns == UINT64_MAX && !timer.timed_out);
	}
	printf("{\"actual_step_sequences\":%u,\"assertions\":%u}\n", sequences, assertions);
#endif
	return 0;
}
