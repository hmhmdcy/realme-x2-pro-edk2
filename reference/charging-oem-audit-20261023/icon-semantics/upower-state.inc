UpDeviceState
up_device_supply_get_state (GUdevDevice *native)
{
	UpDeviceState state;
	gchar *status;

	status = up_device_supply_get_string (native, "status");
	if (status == NULL ||
	    g_ascii_strcasecmp (status, "unknown") == 0 ||
	    *status == '\0') {
		state = UP_DEVICE_STATE_UNKNOWN;
	} else if (g_ascii_strcasecmp (status, "charging") == 0)
		state = UP_DEVICE_STATE_CHARGING;
	else if (g_ascii_strcasecmp (status, "discharging") == 0)
		state = UP_DEVICE_STATE_DISCHARGING;
	else if (g_ascii_strcasecmp (status, "full") == 0)
		state = UP_DEVICE_STATE_FULLY_CHARGED;
	else if (g_ascii_strcasecmp (status, "empty") == 0)
		state = UP_DEVICE_STATE_EMPTY;
	else if (g_ascii_strcasecmp (status, "not charging") == 0)
		state = UP_DEVICE_STATE_PENDING_CHARGE;
	else {
		g_warning ("unknown status string: %s", status);
		state = UP_DEVICE_STATE_UNKNOWN;
	}

	g_free (status);

	return state;
}
