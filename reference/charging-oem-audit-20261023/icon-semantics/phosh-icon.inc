  is_charging = state == UP_DEVICE_STATE_CHARGING;
  smallest_ten = floor (percentage / 10.0) * 10;
  is_charged = state == UP_DEVICE_STATE_FULLY_CHARGED || (is_charging && smallest_ten == 100);

  if (is_charged) {
    icon_name = g_strdup ("battery-level-100-charged-symbolic");
  } else {
    if (is_charging)
      icon_name = g_strdup_printf ("battery-level-%d-charging-symbolic", smallest_ten);
    else
      icon_name = g_strdup_printf ("battery-level-%d-symbolic", smallest_ten);
  }

