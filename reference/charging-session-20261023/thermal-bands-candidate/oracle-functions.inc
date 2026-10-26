static void battery_temp_anti_shake_handle(struct oplus_chg_chip *chip)
{
	int tbatt_cur_shake = chip->temperature, low_shake = 0, high_shake = 0;
	int low_shake_0c = 0, high_shake_0c = 0;

	if (tbatt_cur_shake > chip->tbatt_pre_shake) {			/*get warmer*/
		low_shake = -HYSTERISIS_DECIDEGC;
		high_shake = 0;
		low_shake_0c = -HYSTERISIS_DECIDEGC_0C;
		high_shake_0c = 0;
	} else if (tbatt_cur_shake < chip->tbatt_pre_shake) {	/*get cooler*/
		low_shake = 0;
		high_shake = HYSTERISIS_DECIDEGC;
		low_shake_0c = 0;
		high_shake_0c = HYSTERISIS_DECIDEGC_0C;
	}
	if (chip->tbatt_status == BATTERY_STATUS__HIGH_TEMP) {										/*>53C*/
		chip->limits.cold_bat_decidegc = chip->anti_shake_bound.cold_bound;						/*-3C*/
		chip->limits.little_cold_bat_decidegc = chip->anti_shake_bound.little_cold_bound;		/*0C*/
		chip->limits.cool_bat_decidegc = chip->anti_shake_bound.cool_bound;						/*5C*/
		chip->limits.little_cool_bat_decidegc = chip->anti_shake_bound.little_cool_bound;		/*12C*/
		chip->limits.normal_bat_decidegc = chip->anti_shake_bound.normal_bound;					/*16C*/
		chip->limits.warm_bat_decidegc = chip->anti_shake_bound.warm_bound;						/*45C*/
		chip->limits.hot_bat_decidegc = chip->anti_shake_bound.hot_bound + low_shake;			/*53C*/
	} else if (chip->tbatt_status == BATTERY_STATUS__LOW_TEMP) {								/*<-3C*/
		chip->limits.cold_bat_decidegc = chip->anti_shake_bound.cold_bound + high_shake;
		chip->limits.little_cold_bat_decidegc = chip->anti_shake_bound.little_cold_bound;
		chip->limits.cool_bat_decidegc = chip->anti_shake_bound.cool_bound;
		chip->limits.little_cool_bat_decidegc = chip->anti_shake_bound.little_cool_bound;
		chip->limits.normal_bat_decidegc = chip->anti_shake_bound.normal_bound;
		chip->limits.warm_bat_decidegc = chip->anti_shake_bound.warm_bound;
		chip->limits.hot_bat_decidegc = chip->anti_shake_bound.hot_bound;
	} else if (chip->tbatt_status == BATTERY_STATUS__COLD_TEMP) {								/*-3C~0C*/
		chip->limits.cold_bat_decidegc = chip->anti_shake_bound.cold_bound + low_shake;
		chip->limits.little_cold_bat_decidegc = chip->anti_shake_bound.little_cold_bound + high_shake_0c;
		chip->limits.cool_bat_decidegc = chip->anti_shake_bound.cool_bound;
		chip->limits.little_cool_bat_decidegc = chip->anti_shake_bound.little_cool_bound;
		chip->limits.normal_bat_decidegc = chip->anti_shake_bound.normal_bound;
		chip->limits.warm_bat_decidegc = chip->anti_shake_bound.warm_bound;
		chip->limits.hot_bat_decidegc = chip->anti_shake_bound.hot_bound;
	} else if (chip->tbatt_status == BATTERY_STATUS__LITTLE_COLD_TEMP) {						/*0C-5C*/
		chip->limits.cold_bat_decidegc = chip->anti_shake_bound.cold_bound;
		chip->limits.little_cold_bat_decidegc = chip->anti_shake_bound.little_cold_bound + low_shake_0c;
		chip->limits.cool_bat_decidegc = chip->anti_shake_bound.cool_bound + high_shake;
		chip->limits.little_cool_bat_decidegc = chip->anti_shake_bound.little_cool_bound;
		chip->limits.normal_bat_decidegc = chip->anti_shake_bound.normal_bound;
		chip->limits.warm_bat_decidegc = chip->anti_shake_bound.warm_bound;
		chip->limits.hot_bat_decidegc = chip->anti_shake_bound.hot_bound;
	} else if (chip->tbatt_status == BATTERY_STATUS__COOL_TEMP) {								/*5C~12C*/
		chip->limits.cold_bat_decidegc = chip->anti_shake_bound.cold_bound;
		chip->limits.little_cold_bat_decidegc = chip->anti_shake_bound.little_cold_bound;
		chip->limits.cool_bat_decidegc = chip->anti_shake_bound.cool_bound + low_shake;
		chip->limits.little_cool_bat_decidegc = chip->anti_shake_bound.little_cool_bound + high_shake;
		chip->limits.normal_bat_decidegc = chip->anti_shake_bound.normal_bound;
		chip->limits.warm_bat_decidegc = chip->anti_shake_bound.warm_bound;
		chip->limits.hot_bat_decidegc = chip->anti_shake_bound.hot_bound;
	} else if (chip->tbatt_status == BATTERY_STATUS__LITTLE_COOL_TEMP) {						/*12C~16C*/
		chip->limits.cold_bat_decidegc = chip->anti_shake_bound.cold_bound;
		chip->limits.little_cold_bat_decidegc = chip->anti_shake_bound.little_cold_bound;
		chip->limits.cool_bat_decidegc = chip->anti_shake_bound.cool_bound;
		chip->limits.little_cool_bat_decidegc = chip->anti_shake_bound.little_cool_bound + low_shake;
		chip->limits.normal_bat_decidegc = chip->anti_shake_bound.normal_bound + high_shake;
		chip->limits.warm_bat_decidegc = chip->anti_shake_bound.warm_bound;
		chip->limits.hot_bat_decidegc = chip->anti_shake_bound.hot_bound;
	} else if (chip->tbatt_status == BATTERY_STATUS__NORMAL) {									/*16C~45C*/
		chip->limits.cold_bat_decidegc = chip->anti_shake_bound.cold_bound;
		chip->limits.little_cold_bat_decidegc = chip->anti_shake_bound.little_cold_bound;
		chip->limits.cool_bat_decidegc = chip->anti_shake_bound.cool_bound;
		chip->limits.little_cool_bat_decidegc = chip->anti_shake_bound.little_cool_bound;
		chip->limits.normal_bat_decidegc = chip->anti_shake_bound.normal_bound;
		chip->limits.warm_bat_decidegc = chip->anti_shake_bound.warm_bound;
		chip->limits.hot_bat_decidegc = chip->anti_shake_bound.hot_bound;
	} else if (chip->tbatt_status == BATTERY_STATUS__WARM_TEMP) {								/*45C~53C*/
		chip->limits.cold_bat_decidegc = chip->anti_shake_bound.cold_bound;
		chip->limits.little_cold_bat_decidegc = chip->anti_shake_bound.little_cold_bound;
		chip->limits.cool_bat_decidegc = chip->anti_shake_bound.cool_bound;
		chip->limits.little_cool_bat_decidegc = chip->anti_shake_bound.little_cool_bound;
		chip->limits.normal_bat_decidegc = chip->anti_shake_bound.normal_bound;
		chip->limits.warm_bat_decidegc = chip->anti_shake_bound.warm_bound + low_shake;
		chip->limits.hot_bat_decidegc = chip->anti_shake_bound.hot_bound + high_shake;
	} else {	/*BATTERY_STATUS__REMOVED								<-19C*/
		chip->limits.cold_bat_decidegc = chip->anti_shake_bound.cold_bound;
		chip->limits.little_cold_bat_decidegc = chip->anti_shake_bound.little_cold_bound;
		chip->limits.cool_bat_decidegc = chip->anti_shake_bound.cool_bound;
		chip->limits.little_cool_bat_decidegc = chip->anti_shake_bound.little_cool_bound;
		chip->limits.normal_bat_decidegc = chip->anti_shake_bound.normal_bound;
		chip->limits.warm_bat_decidegc = chip->anti_shake_bound.warm_bound;
		chip->limits.hot_bat_decidegc = chip->anti_shake_bound.hot_bound;
	}
	chip->tbatt_pre_shake = tbatt_cur_shake;
}

static bool oplus_chg_check_tbatt_is_good(struct oplus_chg_chip *chip)
{
	static bool ret = true;
	static int temp_counts = 0;
	int batt_temp = chip->temperature;
	OPLUS_CHG_TBATT_STATUS tbatt_status = chip->tbatt_status;

	if (batt_temp > chip->limits.hot_bat_decidegc || batt_temp < chip->limits.cold_bat_decidegc) {
		temp_counts++;
		if (temp_counts >= TEMP_CNT) {
			temp_counts = 0;
			ret = false;
			if (batt_temp <= chip->limits.removed_bat_decidegc) {
				tbatt_status = BATTERY_STATUS__REMOVED;
			} else if (batt_temp > chip->limits.hot_bat_decidegc) {
				tbatt_status = BATTERY_STATUS__HIGH_TEMP;
			} else {
				tbatt_status = BATTERY_STATUS__LOW_TEMP;
			}
		}
	} else {
		temp_counts = 0;
		ret = true;
		if (batt_temp >= chip->limits.warm_bat_decidegc) {						/*45C*/
			tbatt_status = BATTERY_STATUS__WARM_TEMP;
		} else if (batt_temp >= chip->limits.normal_bat_decidegc) {				/*16C*/
			tbatt_status = BATTERY_STATUS__NORMAL;
		} else if (batt_temp >= chip->limits.little_cool_bat_decidegc) {		/*12C*/
			tbatt_status = BATTERY_STATUS__LITTLE_COOL_TEMP;
		} else if (batt_temp >= chip->limits.cool_bat_decidegc) {				/*5C*/
			tbatt_status = BATTERY_STATUS__COOL_TEMP;
		} else if (batt_temp >= chip->limits.little_cold_bat_decidegc) {		/*0C*/
			tbatt_status = BATTERY_STATUS__LITTLE_COLD_TEMP;
		} else if (batt_temp >= chip->limits.cold_bat_decidegc) {				/*-3C*/
			tbatt_status = BATTERY_STATUS__COLD_TEMP;
		} else {
			tbatt_status = BATTERY_STATUS__COLD_TEMP;
		}
	}
	if (tbatt_status == BATTERY_STATUS__REMOVED) {
		chip->batt_exist = false;
	} else {
		chip->batt_exist = true;
	}
	if (chip->tbatt_pre_shake == TBATT_PRE_SHAKE_INVALID) {
		chip->tbatt_pre_shake = batt_temp;
	}
	if (tbatt_status != chip->tbatt_status) {
		if (chip->tbatt_status == BATTERY_STATUS__WARM_TEMP
					|| chip->tbatt_status == BATTERY_STATUS__COLD_TEMP) {
			if (chip->soc != 100 && chip->batt_full == true
					&& chip->charging_state == CHARGING_STATUS_FULL) {
				chip->batt_full = false;
				chip->tbatt_when_full = 200;
				oplus_chg_voter_charging_start(chip, CHG_STOP_VOTER__FULL);
			}
		}
		chip->tbatt_status = tbatt_status;
		vbatt_higherthan_4180mv = false;
		if (oplus_vooc_get_allow_reading() == true) {
			oplus_chg_set_float_voltage(chip);
			oplus_chg_set_charging_current(chip);
		}
		battery_temp_anti_shake_handle(chip);
	}
	return ret;
}

static void battery_temp_normal_anti_shake_handle(struct oplus_chg_chip *chip)
{
        int tbatt_normal_cur_shake = chip->temperature, low_shake = 0, high_shake = 0;

        if (tbatt_normal_cur_shake > chip->tbatt_normal_pre_shake) {                  /*get warmer*/
                low_shake = -HYSTERISIS_DECIDEGC;
                high_shake = 0;
        } else if (tbatt_normal_cur_shake < chip->tbatt_normal_pre_shake) {   /*get cooler*/
                low_shake = 0;
                high_shake = HYSTERISIS_DECIDEGC;
        }

	if (chip->tbatt_normal_status == BATTERY_STATUS__NORMAL_PHASE1) {
		chip->limits.normal_phase1_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase1_bound;
		chip->limits.normal_phase2_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase2_bound + high_shake;
		chip->limits.normal_phase3_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase3_bound;
		chip->limits.normal_phase4_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase4_bound;
		chip->limits.normal_phase5_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase5_bound;
		chip->limits.normal_phase6_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase6_bound;
	} else if (chip->tbatt_normal_status == BATTERY_STATUS__NORMAL_PHASE2) {
		chip->limits.normal_phase1_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase1_bound;
		chip->limits.normal_phase2_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase2_bound + low_shake;
		chip->limits.normal_phase3_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase3_bound + high_shake;
		chip->limits.normal_phase4_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase4_bound;
		chip->limits.normal_phase5_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase5_bound;
		chip->limits.normal_phase6_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase6_bound;
	} else if (chip->tbatt_normal_status == BATTERY_STATUS__NORMAL_PHASE3) {
		chip->limits.normal_phase1_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase1_bound;
		chip->limits.normal_phase2_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase2_bound;
		chip->limits.normal_phase3_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase3_bound + low_shake;
		chip->limits.normal_phase4_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase4_bound + high_shake;
		chip->limits.normal_phase5_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase5_bound;
		chip->limits.normal_phase6_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase6_bound;
	} else if (chip->tbatt_normal_status == BATTERY_STATUS__NORMAL_PHASE4) {
		chip->limits.normal_phase1_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase1_bound;
		chip->limits.normal_phase2_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase2_bound;
		chip->limits.normal_phase3_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase3_bound;
		chip->limits.normal_phase4_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase4_bound + low_shake;
		chip->limits.normal_phase5_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase5_bound + high_shake;
		chip->limits.normal_phase6_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase6_bound;
	} else if (chip->tbatt_normal_status == BATTERY_STATUS__NORMAL_PHASE5) {
		chip->limits.normal_phase1_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase1_bound;
		chip->limits.normal_phase2_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase2_bound;
		chip->limits.normal_phase3_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase3_bound;
		chip->limits.normal_phase4_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase4_bound;
		chip->limits.normal_phase5_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase5_bound + low_shake;
		chip->limits.normal_phase6_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase6_bound + high_shake;
	} else if (chip->tbatt_normal_status == BATTERY_STATUS__NORMAL_PHASE6) {
		chip->limits.normal_phase1_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase1_bound;
		chip->limits.normal_phase2_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase2_bound;
		chip->limits.normal_phase3_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase3_bound;
		chip->limits.normal_phase4_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase4_bound;
		chip->limits.normal_phase5_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase5_bound;
		chip->limits.normal_phase6_bat_decidegc = chip->tbatt_normal_anti_shake_bound.phase6_bound + low_shake;
	} else {
		/*do nothing*/
	}

	chip->tbatt_normal_pre_shake = tbatt_normal_cur_shake;
}

static void oplus_chg_check_tbatt_normal_status(struct oplus_chg_chip *chip)
{
        int batt_temp = chip->temperature;
        OPLUS_CHG_TBATT_NORMAL_STATUS tbatt_normal_status = chip->tbatt_normal_status;

	if (chip->tbatt_status == BATTERY_STATUS__NORMAL) {
		if (batt_temp >= chip->limits.normal_phase6_bat_decidegc) {
			tbatt_normal_status = BATTERY_STATUS__NORMAL_PHASE6;
		} else if (batt_temp >= chip->limits.normal_phase5_bat_decidegc) {
			tbatt_normal_status = BATTERY_STATUS__NORMAL_PHASE5;
		} else if (batt_temp >= chip->limits.normal_phase4_bat_decidegc) {
			tbatt_normal_status = BATTERY_STATUS__NORMAL_PHASE4;
		} else if (batt_temp >= chip->limits.normal_phase3_bat_decidegc) {
			tbatt_normal_status = BATTERY_STATUS__NORMAL_PHASE3;
		} else if (batt_temp >= chip->limits.normal_phase2_bat_decidegc) {
			tbatt_normal_status = BATTERY_STATUS__NORMAL_PHASE2;
		} else if (batt_temp >= chip->limits.normal_phase1_bat_decidegc) {
			tbatt_normal_status = BATTERY_STATUS__NORMAL_PHASE1;
                } else {
			/*do nothing*/
		}
	}

	if (chip->tbatt_normal_pre_shake == TBATT_PRE_SHAKE_INVALID) {
		chip->tbatt_pre_shake = batt_temp;
	}

	if (chip->tbatt_normal_status != tbatt_normal_status) {
		chip->tbatt_normal_status = tbatt_normal_status;
		if (oplus_vooc_get_allow_reading() == true) {
			oplus_chg_set_float_voltage(chip);
			oplus_chg_set_charging_current(chip);
		}
		battery_temp_normal_anti_shake_handle(chip);
		chg_debug("tbatt_normal_status status change, [%d %d %d %d %d %d %d]\n", chip->tbatt_normal_status,
					chip->limits.normal_phase1_bat_decidegc, chip->limits.normal_phase2_bat_decidegc,
					chip->limits.normal_phase3_bat_decidegc, chip->limits.normal_phase4_bat_decidegc,
					chip->limits.normal_phase5_bat_decidegc, chip->limits.normal_phase6_bat_decidegc);
	}
}

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
