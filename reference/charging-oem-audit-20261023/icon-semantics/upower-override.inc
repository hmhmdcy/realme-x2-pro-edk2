	values.state = up_device_supply_get_state (native);

	if (values.state != UP_DEVICE_STATE_FULLY_CHARGED &&
	    g_udev_device_get_sysfs_attr_as_double_uncached (native, "current_now") < 0.0)
		values.state = UP_DEVICE_STATE_DISCHARGING;

