/* Exact pinned OEM function bodies; host-only audit fixture. */
static int oplus_chg_get_float_voltage(struct oplus_chg_chip *chip)
{
	int flv = chip->limits.temp_normal_vfloat_mv;

	switch (chip->tbatt_status) {
		case BATTERY_STATUS__INVALID:
		case BATTERY_STATUS__REMOVED:
		case BATTERY_STATUS__LOW_TEMP:
		case BATTERY_STATUS__HIGH_TEMP:
			return flv;
		case BATTERY_STATUS__COLD_TEMP:
			flv = chip->limits.temp_cold_vfloat_mv;
			break;
		case BATTERY_STATUS__LITTLE_COLD_TEMP:
			flv = chip->limits.temp_little_cold_vfloat_mv;
			break;
		case BATTERY_STATUS__COOL_TEMP:
			flv = chip->limits.temp_cool_vfloat_mv;
			break;
		case BATTERY_STATUS__LITTLE_COOL_TEMP:
			flv = chip->limits.temp_little_cool_vfloat_mv;
		break;
		case BATTERY_STATUS__NORMAL:
			flv = chip->limits.temp_normal_vfloat_mv;
			break;
		case BATTERY_STATUS__WARM_TEMP:
			flv = chip->limits.temp_warm_vfloat_mv;
			break;
		default:
			break;
	}
	if (oplus_short_c_batt_is_prohibit_chg(chip)
			&& flv > chip->limits.short_c_bat_vfloat_mv) {
		flv = chip->limits.short_c_bat_vfloat_mv;
	}
	return flv;
}

static int oplus_chg_check_sw_full(struct oplus_chg_chip *chip)
{
	int vbatt_full_vol_sw = 0;

	if (!chip->charger_exist) {
		chip->sw_full_count = 0;
		chip->sw_full = false;
		return false;
	}

	if (chip->tbatt_status == BATTERY_STATUS__COLD_TEMP) {
		vbatt_full_vol_sw = chip->limits.cold_vfloat_sw_limit;
	} else if (chip->tbatt_status == BATTERY_STATUS__LITTLE_COLD_TEMP) {
		vbatt_full_vol_sw = chip->limits.little_cold_vfloat_sw_limit;
	} else if (chip->tbatt_status == BATTERY_STATUS__COOL_TEMP) {
		vbatt_full_vol_sw = chip->limits.cool_vfloat_sw_limit;
	} else if (chip->tbatt_status == BATTERY_STATUS__LITTLE_COOL_TEMP) {
		vbatt_full_vol_sw = chip->limits.little_cool_vfloat_sw_limit;
	} else if (chip->tbatt_status == BATTERY_STATUS__NORMAL) {
		vbatt_full_vol_sw = chip->limits.normal_vfloat_sw_limit;
	} else if (chip->tbatt_status == BATTERY_STATUS__WARM_TEMP) {
		vbatt_full_vol_sw = chip->limits.warm_vfloat_sw_limit;
	} else {
		chip->sw_full_count = 0;
		chip->sw_full = 0;
		return false;
	}
	if ((!chip->authenticate) || (!chip->hmac)) {
		vbatt_full_vol_sw = chip->limits.non_standard_vfloat_sw_limit;
	}
	if (oplus_short_c_batt_is_prohibit_chg(chip)) {
		vbatt_full_vol_sw = chip->limits.short_c_bat_vfloat_sw_limit;
	}
	/* use SW Vfloat to check */
	if (chip->batt_volt > vbatt_full_vol_sw) {
		if (chip->icharging < 0 && (chip->icharging * -1) <= chip->limits.iterm_ma) {
			chip->sw_full_count++;
			if (chip->sw_full_count > FULL_COUNTS_SW) {
				chip->sw_full_count = 0;
				chip->sw_full = true;
			}
		} else if (chip->icharging >= 0) {
			chip->sw_full_count++;
			if (chip->sw_full_count > FULL_COUNTS_SW * 2) {
				chip->sw_full_count = 0;
				chip->sw_full = true;
				charger_xlog_printk(CHG_LOG_CRTI,
					"[BATTERY] Battery full by sw when icharging>=0!!\n");
			}
		} else {
			chip->sw_full_count = 0;
			chip->sw_full = false;
		}
	} else {
		chip->sw_full_count = 0;
		chip->sw_full = false;
	}
	return chip->sw_full;
}

static int oplus_chg_check_hw_full(struct oplus_chg_chip *chip)
{
	int vbatt_full_vol_hw = 0;
	static int vbat_counts_hw = 0;
	static bool ret_hw = false;

	if (!chip->charger_exist) {
		vbat_counts_hw = 0;
		ret_hw = false;
		return false;
	}
	vbatt_full_vol_hw = oplus_chg_get_float_voltage(chip);
	if (chip->tbatt_status == BATTERY_STATUS__COLD_TEMP) {
		vbatt_full_vol_hw = chip->limits.temp_cold_vfloat_mv
			+ chip->limits.non_normal_vterm_hw_inc;
	} else if (chip->tbatt_status == BATTERY_STATUS__LITTLE_COLD_TEMP) {
		vbatt_full_vol_hw = chip->limits.temp_little_cold_vfloat_mv
			+ chip->limits.non_normal_vterm_hw_inc;
	} else if (chip->tbatt_status == BATTERY_STATUS__COOL_TEMP) {
		vbatt_full_vol_hw = chip->limits.temp_cool_vfloat_mv
			+ chip->limits.non_normal_vterm_hw_inc;
	} else if (chip->tbatt_status == BATTERY_STATUS__LITTLE_COOL_TEMP) {
		vbatt_full_vol_hw = chip->limits.temp_little_cool_vfloat_mv
			+ chip->limits.non_normal_vterm_hw_inc;
	} else if (chip->tbatt_status == BATTERY_STATUS__NORMAL) {
		vbatt_full_vol_hw = chip->limits.temp_normal_vfloat_mv
			+ chip->limits.normal_vterm_hw_inc;
	} else if (chip->tbatt_status == BATTERY_STATUS__WARM_TEMP) {
		vbatt_full_vol_hw = chip->limits.temp_warm_vfloat_mv
			+ chip->limits.non_normal_vterm_hw_inc;
	} else {
		vbat_counts_hw = 0;
		ret_hw = 0;
		return false;
	}
	if ((!chip->authenticate) || (!chip->hmac)) {
		vbatt_full_vol_hw = chip->limits.non_standard_vfloat_mv
			+ chip->limits.non_normal_vterm_hw_inc;
	}
	if (oplus_short_c_batt_is_prohibit_chg(chip)) {
		vbatt_full_vol_hw = chip->limits.short_c_bat_vfloat_mv
			+ chip->limits.non_normal_vterm_hw_inc;
	}
	/* use HW Vfloat to check */
	if (chip->batt_volt >= vbatt_full_vol_hw) {
		vbat_counts_hw++;
		if (vbat_counts_hw >= FULL_COUNTS_HW) {
			vbat_counts_hw = 0;
			ret_hw = true;
		}
	} else {
		vbat_counts_hw = 0;
		ret_hw = false;
	}
	return ret_hw;
}

static void oplus_chg_check_rechg_status(struct oplus_chg_chip *chip)
{
	int recharging_vol;
	int nbat_vol = chip->batt_volt;
	static int rechging_cnt = 0;

	if (chip->tbatt_status == BATTERY_STATUS__COLD_TEMP) {				//4.0
		recharging_vol = oplus_chg_get_float_voltage(chip) - 300;
	} else if (chip->tbatt_status == BATTERY_STATUS__LITTLE_COLD_TEMP) {//4.4
		recharging_vol = oplus_chg_get_float_voltage(chip) - 200;
	} else {
		recharging_vol = oplus_chg_get_float_voltage(chip);//warm 4.1
		if (recharging_vol > chip->limits.temp_normal_vfloat_mv) {
			recharging_vol = chip->limits.temp_normal_vfloat_mv;
		}
		recharging_vol = recharging_vol - chip->limits.recharge_mv;
	}
	if ((!chip->authenticate) ||(!chip->hmac)) {
		recharging_vol = chip->limits.non_standard_vfloat_mv - 400;//3.80
	}
	if (nbat_vol <= recharging_vol) {
		rechging_cnt++;
	} else {
		rechging_cnt = 0;
	}

	/*don't rechg here unless prohibit rechg is false*/
	if (oplus_short_c_batt_is_disable_rechg(chip)) {
		if (rechging_cnt >= D_RECHGING_CNT) {
			charger_xlog_printk(CHG_LOG_CRTI,
				"[Battery] disable rechg! batt_volt = %d, nReChgingVol = %d\r\n",
				nbat_vol, recharging_vol);
			rechging_cnt = D_RECHGING_CNT;
		}
	}
	if (rechging_cnt > D_RECHGING_CNT) {
		charger_xlog_printk(CHG_LOG_CRTI,
			"[Battery] Battery rechg begin! batt_volt = %d, recharging_vol = %d\n",
			nbat_vol, recharging_vol);
		rechging_cnt = 0;
		chip->in_rechging = true;
		oplus_chg_voter_charging_start(chip, CHG_STOP_VOTER__FULL);/*now rechging!*/
	}
}

static void oplus_chg_full_action(struct oplus_chg_chip *chip)
{
	charger_xlog_printk(CHG_LOG_CRTI, "[BATTERY] Battery full !!\n");
	oplus_chg_voter_charging_stop(chip, CHG_STOP_VOTER__FULL);
	/*chip->charging_state = CHARGING_STATUS_FULL;*/
	if(chip->batt_full == false) {
		chip->tbatt_when_full = chip->temperature;
	}
	chip->batt_full = true;
	chip->total_time = 0;
	chip->in_rechging = false;
	chip->limits.vfloat_over_counts = 0;
	oplus_chg_check_rechg_status(chip);
}

static int bq27541_get_average_current(void)
{
	int ret;
	int curr = 0;

	if (!gauge_ic) {
		return 0;
	}
	if (atomic_read(&gauge_ic->suspended) == 1) {
		return -gauge_ic->current_pre;
	}
	if (oplus_vooc_get_allow_reading() == true) {
		ret = bq27541_read_i2c(gauge_ic->cmd_addr.reg_ai, &curr);
		if (ret) {
			dev_err(gauge_ic->dev, "error reading current.\n");
			return gauge_ic->current_pre;
		}
	} else {
		return -gauge_ic->current_pre;
	}
	/* negative current */
	if (curr&0x8000) {
		curr = -((~(curr-1))&0xFFFF);
	}
	gauge_ic->current_pre = curr;
	return -curr;
}
