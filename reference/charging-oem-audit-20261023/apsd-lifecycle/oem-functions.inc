/* drivers/power/supply/qcom/smb5-lib.c:982 */
void smblib_apsd_enable(struct smb_charger *chg, bool enable)
{
	int rc;

	rc = smblib_masked_write(chg, USBIN_OPTIONS_1_CFG_REG,
				BC1P2_SRC_DETECT_BIT,
				enable ? BC1P2_SRC_DETECT_BIT : 0);
	if (rc < 0)
		smblib_err(chg, "failed to write USBIN_OPTIONS_1_CFG rc=%d\n",
				rc);
}

/* drivers/power/supply/qcom/smb5-lib.c:1033 */
static int smblib_request_dpdm(struct smb_charger *chg, bool enable)
{
	int rc = 0;

	if (chg->pr_swap_in_progress)
		return 0;

	/* fetch the DPDM regulator */
	if (!chg->dpdm_reg && of_get_property(chg->dev->of_node,
				"dpdm-supply", NULL)) {
		chg->dpdm_reg = devm_regulator_get(chg->dev, "dpdm");
		if (IS_ERR(chg->dpdm_reg)) {
			rc = PTR_ERR(chg->dpdm_reg);
			smblib_err(chg, "Couldn't get dpdm regulator rc=%d\n",
					rc);
			chg->dpdm_reg = NULL;
			return rc;
		}
	}

	if (enable) {
		if (chg->dpdm_reg && !regulator_is_enabled(chg->dpdm_reg)) {
			smblib_dbg(chg, PR_MISC, "enabling DPDM regulator\n");
			rc = regulator_enable(chg->dpdm_reg);
			if (rc < 0)
				smblib_err(chg,
					"Couldn't enable dpdm regulator rc=%d\n",
					rc);
		}
	} else {
		if (chg->dpdm_reg && regulator_is_enabled(chg->dpdm_reg)) {
			smblib_dbg(chg, PR_MISC, "disabling DPDM regulator\n");
			rc = regulator_disable(chg->dpdm_reg);
			if (rc < 0)
				smblib_err(chg,
					"Couldn't disable dpdm regulator rc=%d\n",
					rc);
		}
	}

	return rc;
}

/* drivers/power/supply/qcom/smb5-lib.c:1076 */
static void smblib_rerun_apsd(struct smb_charger *chg)
{
	int rc;

	smblib_dbg(chg, PR_MISC, "re-running APSD\n");

	rc = smblib_masked_write(chg, CMD_APSD_REG,
				APSD_RERUN_BIT, APSD_RERUN_BIT);
	if (rc < 0)
		smblib_err(chg, "Couldn't re-run APSD rc=%d\n", rc);
}

/* drivers/power/supply/qcom/smb5-lib.c:1385 */
int smblib_rerun_apsd_if_required(struct smb_charger *chg)
{
#ifdef VENDOR_EDIT
/* Jianchao.Shi@BSP.CHG.Basic, 2018/01/19, sjc Add for charging */
	const struct apsd_result *apsd_result;
#endif
	union power_supply_propval val;
	int rc;

	rc = smblib_get_prop_usb_present(chg, &val);
	if (rc < 0) {
		smblib_err(chg, "Couldn't get usb present rc = %d\n", rc);
		return rc;
	}

	if (!val.intval)
		return 0;

#ifdef VENDOR_EDIT
/* Jianchao.Shi@BSP.CHG.Basic, 2017/06/19, sjc Add to rerun apsd */
	apsd_result = smblib_get_apsd_result(chg);
	if ((apsd_result->pst != POWER_SUPPLY_TYPE_UNKNOWN)
		&& (apsd_result->pst != POWER_SUPPLY_TYPE_USB)
		&& (apsd_result->pst != POWER_SUPPLY_TYPE_USB_CDP))
		/* if type is not usb or unknown no need to rerun apsd */
		return 0;
#endif

	rc = smblib_request_dpdm(chg, true);
	if (rc < 0)
		smblib_err(chg, "Couldn't to enable DPDM rc=%d\n", rc);

	chg->uusb_apsd_rerun_done = true;
	smblib_rerun_apsd(chg);

	return 0;
}

/* drivers/power/supply/qcom/smb5-lib.c:5080 */
void smblib_usb_plugin_locked(struct smb_charger *chg)
{
	int rc;
	u8 stat;
	bool vbus_rising;
	struct smb_irq_data *data;
	struct storm_watch *wdata;

	rc = smblib_read(chg, USBIN_BASE + INT_RT_STS_OFFSET, &stat);
	if (rc < 0) {
		smblib_err(chg, "Couldn't read USB_INT_RT_STS rc=%d\n", rc);
		return;
	}

	vbus_rising = (bool)(stat & USBIN_PLUGIN_RT_STS_BIT);
	smblib_set_opt_switcher_freq(chg, vbus_rising ? chg->chg_freq.freq_5V :
						chg->chg_freq.freq_removal);

#ifdef VENDOR_EDIT
/* Jianchao.Shi@BSP.CHG.Basic, 2016/12/20, sjc Add for charging */
	printk(KERN_ERR "!!!!! smblib_usb_plugin_locked: [%d]\n", vbus_rising);
#endif

	if (vbus_rising) {
#ifdef VENDOR_EDIT
/* Jianchao.Shi@BSP.CHG.Basic, 2016/12/20, sjc Add for charging */
		if (smblib_get_prop_dfp_mode(chg) != POWER_SUPPLY_TYPEC_NONE) {
			chg->fake_usb_insertion = true;
			return;
		}
#endif
		cancel_delayed_work_sync(&chg->pr_swap_detach_work);
		vote(chg->awake_votable, DETACH_DETECT_VOTER, false, 0);
		rc = smblib_request_dpdm(chg, true);
		if (rc < 0)
			smblib_err(chg, "Couldn't to enable DPDM rc=%d\n", rc);

		/* Enable SW Thermal regulation */
		rc = smblib_set_sw_thermal_regulation(chg, true);
		if (rc < 0)
			smblib_err(chg, "Couldn't start SW thermal regulation WA, rc=%d\n",
				rc);

		/* Remove FCC_STEPPER 1.5A init vote to allow FCC ramp up */
		if (chg->fcc_stepper_enable)
			vote(chg->fcc_votable, FCC_STEPPER_VOTER, false, 0);


#ifdef VENDOR_EDIT
/* Jianchao.Shi@BSP.CHG.Basic, 2018/04/13, sjc Add for charging */
		schedule_delayed_work(&chg->typec_disable_cmd_work, msecs_to_jiffies(500));
#endif
		/* Schedule work to enable parallel charger */
		vote(chg->awake_votable, PL_DELAY_VOTER, true, 0);
		schedule_delayed_work(&chg->pl_enable_work,
					msecs_to_jiffies(PL_DELAY_MS));
	} else {
#ifdef VENDOR_EDIT
/* Jianchao.Shi@BSP.CHG.Basic, 2017/01/22, sjc Add for charging */
		if (chg->fake_usb_insertion) {
			chg->fake_usb_insertion = false;
			return;
		}

		oppo_vooc_reset_fastchg_after_usbout();
		if (oppo_vooc_get_fastchg_started() == false && g_oppo_chip) {
			///smbchg_set_chargerid_switch_val(0);
			cancel_work_sync(&chg->chargerid_switch_work);
			schedule_work(&chg->chargerid_switch_work);
			g_oppo_chip->chargerid_volt = 0;
			g_oppo_chip->chargerid_volt_got = false;
			g_oppo_chip->charger_type = POWER_SUPPLY_TYPE_UNKNOWN;
			oppo_chg_wake_update_work();
		}
		chg->pre_current_ma = -1;
#endif
#ifdef VENDOR_EDIT
/* Jianchao.Shi@BSP.CHG.Basic, 2018/04/24, sjc Add to rerun apsd */
		chg->uusb_apsd_rerun_done = false;
#endif
		/* Disable SW Thermal Regulation */
		rc = smblib_set_sw_thermal_regulation(chg, false);
		if (rc < 0)
			smblib_err(chg, "Couldn't stop SW thermal regulation WA, rc=%d\n",
				rc);

		if (chg->wa_flags & BOOST_BACK_WA) {
			data = chg->irq_info[SWITCHER_POWER_OK_IRQ].irq_data;
			if (data) {
				wdata = &data->storm_data;
				update_storm_count(wdata,
						WEAK_CHG_STORM_COUNT);
				vote(chg->usb_icl_votable, BOOST_BACK_VOTER,
						false, 0);
				vote(chg->usb_icl_votable, WEAK_CHARGER_VOTER,
						false, 0);
			}
		}

		/* Force 1500mA FCC on removal if fcc stepper is enabled */
		if (chg->fcc_stepper_enable)
			vote(chg->fcc_votable, FCC_STEPPER_VOTER,
							true, 1500000);

		if (chg->wa_flags & WEAK_ADAPTER_WA) {
			chg->aicl_5v_threshold_mv =
					chg->default_aicl_5v_threshold_mv;
			chg->aicl_cont_threshold_mv =
					chg->default_aicl_cont_threshold_mv;

			smblib_set_charge_param(chg,
					&chg->param.aicl_5v_threshold,
					chg->aicl_5v_threshold_mv);
			smblib_set_charge_param(chg,
					&chg->param.aicl_cont_threshold,
					chg->aicl_cont_threshold_mv);
			chg->aicl_max_reached = false;

			if (chg->smb_version == PMI632_SUBTYPE)
				schgm_flash_torch_priority(chg,
						TORCH_BUCK_MODE);

			data = chg->irq_info[USBIN_UV_IRQ].irq_data;
			if (data) {
				wdata = &data->storm_data;
				reset_storm_count(wdata);
			}
			vote(chg->usb_icl_votable, AICL_THRESHOLD_VOTER,
					false, 0);
		}

		rc = smblib_request_dpdm(chg, false);
		if (rc < 0)
			smblib_err(chg, "Couldn't disable DPDM rc=%d\n", rc);

		smblib_update_usb_type(chg);
	}

	if (chg->connector_type == POWER_SUPPLY_CONNECTOR_MICRO_USB)
		smblib_micro_usb_plugin(chg, vbus_rising);

#ifdef VENDOR_EDIT
/* Jianchao.Shi@BSP.CHG.Basic, 2017/03/25, sjc Add for charging */
	if (vbus_rising) {
		cancel_delayed_work_sync(&chg->chg_monitor_work);
		schedule_delayed_work(&chg->chg_monitor_work, OPPO_CHG_MONITOR_INTERVAL);
	} else {
    	fg_oppo_set_input_current = false;
		cancel_delayed_work_sync(&chg->chg_monitor_work);
	}
#endif

#ifdef VENDOR_EDIT
/* Jianchao.Shi@BSP.CHG.Basic, 2018/07/13, sjc Add for fake typec */
	if (chg->fake_typec_insertion == true && !vbus_rising) {
		printk(KERN_ERR "!!! %s: fake typec unplug\n", __func__);
		chg->fake_typec_insertion = false;
		chg->typec_mode = POWER_SUPPLY_TYPEC_NONE;
	}
#endif

#ifdef VENDOR_EDIT
/* Cong.Dai@BSP.TP.Init, 2018/04/08, Add for notify touchpanel status */
	if (vbus_rising) {
		switch_usb_state(1);
	} else {
		switch_usb_state(0);
	}
#endif

	power_supply_changed(chg->usb_psy);
	smblib_dbg(chg, PR_INTERRUPT, "IRQ: usbin-plugin %s\n",
					vbus_rising ? "attached" : "detached");
}

/* drivers/power/supply/qcom/smb5-lib.c:5255 */
irqreturn_t usb_plugin_irq_handler(int irq, void *data)
{
	struct smb_irq_data *irq_data = data;
	struct smb_charger *chg = irq_data->parent_data;
#ifdef VENDOR_EDIT//Fanhong.Kong@ProDrv.CHG,add 2018/06/02 for SVOOC OTG	
	struct oppo_chg_chip *chip = g_oppo_chip;
		if (chg->typec_mode == POWER_SUPPLY_TYPEC_SINK
			&& chip->vbatt_num == 2 ) {
			pr_info("%s:chg->typec_mode = sink return!\n", __func__);
			return IRQ_HANDLED;
		}
#endif/*VENDOR_EDIT*/
	if (chg->pd_hard_reset)
		smblib_usb_plugin_hard_reset_locked(chg);
	else
		smblib_usb_plugin_locked(chg);

	return IRQ_HANDLED;
}

/* drivers/power/supply/qcom/smb5-lib.c:5458 */
irqreturn_t usb_source_change_irq_handler(int irq, void *data)
{
	struct smb_irq_data *irq_data = data;
	struct smb_charger *chg = irq_data->parent_data;
	int rc = 0;
	u8 stat;
#ifdef VENDOR_EDIT
/* Jianchao.Shi@BSP.CHG.Basic, 2017/06/19, sjc Add to rerun apsd */
	u8 reg_value = 0;
#endif
#ifdef VENDOR_EDIT//Fanhong.Kong@ProDrv.CHG,add 2018/06/02 for SVOOC OTG
	struct oppo_chg_chip *chip = g_oppo_chip;

	if (chg->typec_mode == POWER_SUPPLY_TYPEC_SINK
		&& chip->vbatt_num == 2 ) {
		pr_info("%s:chg->typec_mode = sink return!\n", __func__);
		return IRQ_HANDLED;
	}
	
	if (chg->fake_usb_insertion)
		return IRQ_HANDLED;
#endif/*VENDOR_EDIT*/
	/* PD session is ongoing, ignore BC1.2 and QC detection */
	if (chg->pd_active)
		return IRQ_HANDLED;

	rc = smblib_read(chg, APSD_STATUS_REG, &stat);
	if (rc < 0) {
		smblib_err(chg, "Couldn't read APSD_STATUS rc=%d\n", rc);
		return IRQ_HANDLED;
	}
	smblib_dbg(chg, PR_INTERRUPT, "APSD_STATUS = 0x%02x\n", stat);

#ifndef VENDOR_EDIT
/* Jianchao.Shi@BSP.CHG.Basic, 2018/04/24, sjc Modify to rerun apsd */
	if ((chg->connector_type == POWER_SUPPLY_CONNECTOR_MICRO_USB)
			&& (stat & APSD_DTC_STATUS_DONE_BIT)
			&& !chg->uusb_apsd_rerun_done) {
#else
	if ((stat & APSD_DTC_STATUS_DONE_BIT) && !chg->uusb_apsd_rerun_done) {
#endif
		/*
		 * Force re-run APSD to handle slow insertion related
		 * charger-mis-detection.
		 */
#ifndef VENDOR_EDIT
/* Jianchao.Shi@BSP.CHG.Basic, 2017/06/19, sjc Modify to rerun apsd */
		chg->uusb_apsd_rerun_done = true;
		smblib_rerun_apsd_if_required(chg);
		return IRQ_HANDLED;
#else
		smblib_read(chg, APSD_RESULT_STATUS_REG, &reg_value);
		if (reg_value & (CDP_CHARGER_BIT | SDP_CHARGER_BIT)) {
			chg->uusb_apsd_rerun_done = true;
			smblib_rerun_apsd(chg);
			return IRQ_HANDLED;
		}
#endif
	}

	smblib_handle_apsd_done(chg,
		(bool)(stat & APSD_DTC_STATUS_DONE_BIT));

#ifdef VENDOR_EDIT
/* Jianchao.Shi@BSP.CHG.Basic, 2017/01/25, sjc Add for charging */
	if ((bool)(stat & APSD_DTC_STATUS_DONE_BIT))
		oppo_chg_wake_update_work();
#endif

	smblib_handle_hvdcp_detect_done(chg,
		(bool)(stat & QC_CHARGER_BIT));

	smblib_handle_hvdcp_check_timeout(chg,
		(bool)(stat & HVDCP_CHECK_TIMEOUT_BIT),
		(bool)(stat & QC_CHARGER_BIT));

	smblib_handle_hvdcp_3p0_auth_done(chg,
		(bool)(stat & QC_AUTH_DONE_STATUS_BIT));

	smblib_handle_sdp_enumeration_done(chg,
		(bool)(stat & ENUMERATION_DONE_BIT));

	smblib_handle_slow_plugin_timeout(chg,
		(bool)(stat & SLOW_PLUGIN_TIMEOUT_BIT));

	smblib_hvdcp_adaptive_voltage_change(chg);

	power_supply_changed(chg->usb_psy);

	rc = smblib_read(chg, APSD_STATUS_REG, &stat);
	if (rc < 0) {
		smblib_err(chg, "Couldn't read APSD_STATUS rc=%d\n", rc);
		return IRQ_HANDLED;
	}
	smblib_dbg(chg, PR_INTERRUPT, "APSD_STATUS = 0x%02x\n", stat);

	return IRQ_HANDLED;
}

/* drivers/power/supply/qcom/smb5-lib.c:5707 */
static void typec_src_insertion(struct smb_charger *chg)
{
	int rc = 0;
	u8 stat;

	if (chg->pr_swap_in_progress)
		return;

	rc = smblib_read(chg, LEGACY_CABLE_STATUS_REG, &stat);
	if (rc < 0) {
		smblib_err(chg, "Couldn't read TYPE_C_STATE_MACHINE_STATUS_REG rc=%d\n",
			rc);
		return;
	}

	chg->typec_legacy = stat & TYPEC_LEGACY_CABLE_STATUS_BIT;
	chg->ok_to_pd = (!(chg->typec_legacy || *chg->pd_disabled)
			|| chg->early_usb_attach) && !chg->pd_not_supported;

	/* allow apsd proceed to detect QC2/3 */
	if (!chg->ok_to_pd)
		smblib_hvdcp_detect_enable(chg, true);
}

/* drivers/power/supply/qcom/smb5-lib.c:5756 */
static void typec_src_removal(struct smb_charger *chg)
{
	int rc;
	struct smb_irq_data *data;
	struct storm_watch *wdata;
	int sec_charger;

	sec_charger = chg->sec_pl_present ? POWER_SUPPLY_CHARGER_SEC_PL :
				POWER_SUPPLY_CHARGER_SEC_NONE;

	rc = smblib_select_sec_charger(chg, sec_charger, POWER_SUPPLY_CP_NONE,
					false);
	if (rc < 0)
		dev_err(chg->dev,
			"Couldn't disable secondary charger rc=%d\n", rc);

	typec_src_fault_condition_cfg(chg, false);
	smblib_hvdcp_detect_enable(chg, false);
	smblib_update_usb_type(chg);

	if (chg->wa_flags & BOOST_BACK_WA) {
		data = chg->irq_info[SWITCHER_POWER_OK_IRQ].irq_data;
		if (data) {
			wdata = &data->storm_data;
			update_storm_count(wdata, WEAK_CHG_STORM_COUNT);
			vote(chg->usb_icl_votable, BOOST_BACK_VOTER, false, 0);
			vote(chg->usb_icl_votable, WEAK_CHARGER_VOTER,
					false, 0);
		}
	}

	cancel_delayed_work_sync(&chg->pl_enable_work);

	/* reset input current limit voters */
	#ifndef VENDOR_EDIT  /* zhangkun@BSP.CHG.Basic, 2019/02/22, Add for charge*/
	vote(chg->usb_icl_votable, SW_ICL_MAX_VOTER, true,
			is_flash_active(chg) ? SDP_CURRENT_UA : SDP_100_MA);
	#else	
	vote(chg->usb_icl_votable, SW_ICL_MAX_VOTER, false, 0);
	#endif
	vote(chg->usb_icl_votable, PD_VOTER, false, 0);
	vote(chg->usb_icl_votable, USB_PSY_VOTER, false, 0);
	vote(chg->usb_icl_votable, DCP_VOTER, false, 0);
	vote(chg->usb_icl_votable, SW_QC3_VOTER, false, 0);
	vote(chg->usb_icl_votable, CTM_VOTER, false, 0);
	vote(chg->usb_icl_votable, HVDCP2_ICL_VOTER, false, 0);
	vote(chg->usb_icl_votable, CHG_TERMINATION_VOTER, false, 0);
	vote(chg->usb_icl_votable, THERMAL_THROTTLE_VOTER, false, 0);

	/* reset usb irq voters */
	vote(chg->limited_irq_disable_votable, CHARGER_TYPE_VOTER,
			true, 0);
	vote(chg->hdc_irq_disable_votable, CHARGER_TYPE_VOTER, true, 0);
	vote(chg->hdc_irq_disable_votable, HDC_IRQ_VOTER, false, 0);

	/* reset parallel voters */
	vote(chg->pl_disable_votable, PL_DELAY_VOTER, true, 0);
	vote(chg->pl_disable_votable, PL_FCC_LOW_VOTER, false, 0);
	vote(chg->pl_enable_votable_indirect, USBIN_I_VOTER, false, 0);
	vote(chg->pl_enable_votable_indirect, USBIN_V_VOTER, false, 0);
	vote(chg->awake_votable, PL_DELAY_VOTER, false, 0);

	/* Remove SW thermal regulation WA votes */
	vote(chg->usb_icl_votable, SW_THERM_REGULATION_VOTER, false, 0);
	vote(chg->pl_disable_votable, SW_THERM_REGULATION_VOTER, false, 0);
	vote(chg->dc_suspend_votable, SW_THERM_REGULATION_VOTER, false, 0);
	if (chg->cp_disable_votable)
		vote(chg->cp_disable_votable, SW_THERM_REGULATION_VOTER,
								false, 0);

	/* reset USBOV votes and cancel work */
	cancel_delayed_work_sync(&chg->usbov_dbc_work);
	vote(chg->awake_votable, USBOV_DBC_VOTER, false, 0);
	chg->dbc_usbov = false;

	chg->pulse_cnt = 0;
	chg->usb_icl_delta_ua = 0;
	chg->voltage_min_uv = MICRO_5V;
	chg->voltage_max_uv = MICRO_5V;
	chg->usbin_forced_max_uv = 0;

	/* write back the default FLOAT charger configuration */
	rc = smblib_masked_write(chg, USBIN_OPTIONS_2_CFG_REG,
				(u8)FLOAT_OPTIONS_MASK, chg->float_cfg);
	if (rc < 0)
		smblib_err(chg, "Couldn't write float charger options rc=%d\n",
			rc);

	/* reconfigure allowed voltage for HVDCP */
	rc = smblib_set_adapter_allowance(chg,
			USBIN_ADAPTER_ALLOW_5V_OR_9V_TO_12V);
	if (rc < 0)
		smblib_err(chg, "Couldn't set USBIN_ADAPTER_ALLOW_5V_OR_9V_TO_12V rc=%d\n",
			rc);

	/*
	 * if non-compliant charger caused UV, restore original max pulses
	 * and turn SUSPEND_ON_COLLAPSE_USBIN_BIT back on.
	 */
	if (chg->qc2_unsupported_voltage) {
		rc = smblib_masked_write(chg, HVDCP_PULSE_COUNT_MAX_REG,
				HVDCP_PULSE_COUNT_MAX_QC2_MASK,
				chg->qc2_max_pulses);
		if (rc < 0)
			smblib_err(chg, "Couldn't restore max pulses rc=%d\n",
					rc);

		rc = smblib_masked_write(chg, USBIN_AICL_OPTIONS_CFG_REG,
				SUSPEND_ON_COLLAPSE_USBIN_BIT,
				SUSPEND_ON_COLLAPSE_USBIN_BIT);
		if (rc < 0)
			smblib_err(chg, "Couldn't turn on SUSPEND_ON_COLLAPSE_USBIN_BIT rc=%d\n",
					rc);

		chg->qc2_unsupported_voltage = QC2_COMPLIANT;
	}

	if (chg->use_extcon)
		smblib_notify_device_mode(chg, false);

	chg->typec_legacy = false;
}

/* drivers/power/supply/qcom/smb5-lib.c:6075 */
irqreturn_t typec_attach_detach_irq_handler(int irq, void *data)
{
	struct smb_irq_data *irq_data = data;
	struct smb_charger *chg = irq_data->parent_data;
	u8 stat;
	int rc;

	smblib_dbg(chg, PR_INTERRUPT, "IRQ: %s\n", irq_data->name);

	rc = smblib_read(chg, TYPE_C_STATE_MACHINE_STATUS_REG, &stat);
	if (rc < 0) {
		smblib_err(chg, "Couldn't read TYPE_C_STATE_MACHINE_STATUS_REG rc=%d\n",
			rc);
		return IRQ_HANDLED;
	}

	if (stat & TYPEC_ATTACH_DETACH_STATE_BIT) {
#ifdef VENDOR_EDIT  /* zhangkun@BSP.CHG.Basic, 2019/02/22, Add for disable water detect*/
		smblib_lpd_clear_ra_open_work(chg);
#else
		cancel_delayed_work_sync(&chg->lpd_detach_work);
		chg->lpd_stage = LPD_STAGE_FLOAT_CANCEL;
		cancel_delayed_work_sync(&chg->lpd_ra_open_work);
		vote(chg->awake_votable, LPD_VOTER, false, 0);
#endif

		rc = smblib_read(chg, TYPE_C_MISC_STATUS_REG, &stat);
		if (rc < 0) {
			smblib_err(chg, "Couldn't read TYPE_C_MISC_STATUS_REG rc=%d\n",
				rc);
			return IRQ_HANDLED;
		}

		if (smblib_get_prop_dfp_mode(chg) ==
				POWER_SUPPLY_TYPEC_SINK_AUDIO_ADAPTER) {
			chg->sink_src_mode = AUDIO_ACCESS_MODE;
			typec_ra_ra_insertion(chg);
		} else if (stat & SNK_SRC_MODE_BIT) {
			if (smblib_src_lpd(chg))
				return IRQ_HANDLED;
			chg->sink_src_mode = SRC_MODE;
			typec_sink_insertion(chg);
		} else {
			chg->sink_src_mode = SINK_MODE;
			typec_src_insertion(chg);
		}

	} else {
		switch (chg->sink_src_mode) {
		case SRC_MODE:
			typec_sink_removal(chg);
			break;
		case SINK_MODE:
		case AUDIO_ACCESS_MODE:
			typec_src_removal(chg);
			break;
		case UNATTACHED_MODE:
		default:
			typec_mode_unattached(chg);
			break;
		}

		if (!chg->pr_swap_in_progress) {
			chg->ok_to_pd = false;
			chg->sink_src_mode = UNATTACHED_MODE;
			chg->early_usb_attach = false;
			smblib_apsd_enable(chg, true);
		}

		if (chg->lpd_stage == LPD_STAGE_FLOAT_CANCEL)
			schedule_delayed_work(&chg->lpd_detach_work,
					msecs_to_jiffies(1000));
	}

	power_supply_changed(chg->usb_psy);

	return IRQ_HANDLED;
}

/* drivers/power/supply/qcom/smb5-lib.c:4319 */
int smblib_set_prop_pd_active(struct smb_charger *chg,
				const union power_supply_propval *val)
{
	const struct apsd_result *apsd = smblib_get_apsd_result(chg);

	int rc = 0;
	int sec_charger;

	chg->pd_active = val->intval;

	smblib_apsd_enable(chg, !chg->pd_active);

	update_sw_icl_max(chg, apsd->pst);

	if (chg->pd_active) {
		vote(chg->limited_irq_disable_votable, CHARGER_TYPE_VOTER,
				false, 0);
		vote(chg->hdc_irq_disable_votable, CHARGER_TYPE_VOTER,
				false, 0);

		/*
		 * Enforce 100mA for PD until the real vote comes in later.
		 * It is guaranteed that pd_active is set prior to
		 * pd_current_max
		 */
		vote(chg->usb_icl_votable, PD_VOTER, true, USBIN_100MA);
		vote(chg->usb_icl_votable, USB_PSY_VOTER, false, 0);
		vote(chg->usb_icl_votable, SW_ICL_MAX_VOTER, false, 0);

		/*
		 * For PPS, Charge Pump is preferred over parallel charger if
		 * present.
		 */
		if (chg->pd_active == POWER_SUPPLY_PD_PPS_ACTIVE
						&& chg->sec_cp_present) {
			rc = smblib_select_sec_charger(chg,
						POWER_SUPPLY_CHARGER_SEC_CP,
						POWER_SUPPLY_CP_PPS, false);
			if (rc < 0)
				dev_err(chg->dev, "Couldn't enable secondary charger rc=%d\n",
					rc);
		}
	} else {
		vote(chg->usb_icl_votable, PD_VOTER, false, 0);
		vote(chg->limited_irq_disable_votable, CHARGER_TYPE_VOTER,
				true, 0);
		vote(chg->hdc_irq_disable_votable, CHARGER_TYPE_VOTER,
				true, 0);

		sec_charger = chg->sec_pl_present ?
						POWER_SUPPLY_CHARGER_SEC_PL :
						POWER_SUPPLY_CHARGER_SEC_NONE;
		rc = smblib_select_sec_charger(chg, sec_charger,
						POWER_SUPPLY_CP_NONE, false);
		if (rc < 0)
			dev_err(chg->dev,
				"Couldn't enable secondary charger rc=%d\n",
					rc);

		/* PD hard resets failed, proceed to detect QC2/3 */
		if (chg->ok_to_pd) {
			chg->ok_to_pd = false;
			smblib_hvdcp_detect_enable(chg, true);
		}
	}

	smblib_update_usb_type(chg);
	power_supply_changed(chg->usb_psy);
	return rc;
}

/* drivers/power/supply/qcom/smb5-lib.c:6561 */
static void smblib_pr_swap_detach_work(struct work_struct *work)
{
	struct smb_charger *chg = container_of(work, struct smb_charger,
						pr_swap_detach_work.work);
	int rc;
	u8 stat;

	rc = smblib_read(chg, TYPE_C_STATE_MACHINE_STATUS_REG, &stat);
	if (rc < 0) {
		smblib_err(chg, "Couldn't read STATE_MACHINE_STS rc=%d\n", rc);
		goto out;
	}
	smblib_dbg(chg, PR_REGISTER, "STATE_MACHINE_STS %x\n", stat);
	if (!(stat & TYPEC_ATTACH_DETACH_STATE_BIT)) {
		rc = smblib_request_dpdm(chg, false);
		if (rc < 0)
			smblib_err(chg, "Couldn't disable DPDM rc=%d\n", rc);
	}
out:
	vote(chg->awake_votable, DETACH_DETECT_VOTER, false, 0);
}

/* drivers/power/supply/qcom/smb5-lib.c:7165 */
static void oppo_chargerid_switch_work(struct work_struct *work)
{
	smbchg_set_chargerid_switch_val(0);
	return;
}

/* drivers/power/supply/qcom/smb5-lib.c:7172 */
static void typec_disable_cmd_work(struct work_struct *work)
{
	int rc = 0;
	struct smb_charger *chg = container_of(work, struct smb_charger, typec_disable_cmd_work.work);

	if (smblib_get_prop_typec_mode(chg) != POWER_SUPPLY_TYPEC_NONE) {
		printk(KERN_ERR "!!! %s: active t-c module\n", __func__);
		return;
	}

	rc = smblib_masked_write(chg, TYPE_C_MODE_CFG_REG, TYPEC_DISABLE_CMD_BIT, TYPEC_DISABLE_CMD_BIT);
	if (rc < 0)
		smblib_err(chg, "Couldn't write TYPE_C_INTRPT_ENB_SOFTWARE_CTRL_REG rc=%d\n", rc);

	msleep(100);

	rc = smblib_masked_write(chg, TYPE_C_MODE_CFG_REG, TYPEC_DISABLE_CMD_BIT, 0);
	if (rc < 0)
		smblib_err(chg, "Couldn't write TYPE_C_INTRPT_ENB_SOFTWARE_CTRL_REG rc=%d\n", rc);

	printk(KERN_ERR "!!! %s: re-active t-c module\n", __func__);

	msleep(200);
	if (smblib_get_prop_typec_mode(chg) == POWER_SUPPLY_TYPEC_NONE) {
		printk(KERN_ERR "!!! %s: fake typec plug\n", __func__);
		rc = smblib_masked_write(chg, TYPE_C_CFG_REG, APSD_START_ON_CC_BIT, 0);
		if (rc < 0)
			smblib_err(chg, "Couldn't enable APSD_START_ON_CC rc=%d\n", rc);
		msleep(600);
		chg->fake_typec_insertion = true;
		chg->typec_mode = POWER_SUPPLY_TYPEC_SOURCE_DEFAULT;
		power_supply_changed(chg->usb_psy);
	}
	return;
}

/* drivers/power/supply/qcom/qpnp-smb5.c:3285 */
static int smb5_configure_typec(struct smb_charger *chg)
{
	union power_supply_propval pval = {0, };
	int rc;
	u8 val = 0;

	rc = smblib_read(chg, LEGACY_CABLE_STATUS_REG, &val);
	if (rc < 0) {
		dev_err(chg->dev, "Couldn't read Legacy status rc=%d\n", rc);
		return rc;
	}

	/*
	 * Across reboot, standard typeC cables get detected as legacy cables
	 * due to VBUS attachment prior to CC attach/dettach. To handle this,
	 * "early_usb_attach" flag is used, which assumes that across reboot,
	 * the cable connected can be standard typeC. However, its jurisdiction
	 * is limited to PD capable designs only. Hence, for non-PD type designs
	 * reset legacy cable detection by disabling/enabling typeC mode.
	 */
	if (chg->pd_not_supported && (val & TYPEC_LEGACY_CABLE_STATUS_BIT)) {
		pval.intval = POWER_SUPPLY_TYPEC_PR_NONE;
		smblib_set_prop_typec_power_role(chg, &pval);
		if (rc < 0) {
			dev_err(chg->dev, "Couldn't disable TYPEC rc=%d\n", rc);
			return rc;
		}

		/* delay before enabling typeC */
		msleep(50);

		pval.intval = POWER_SUPPLY_TYPEC_PR_DUAL;
		smblib_set_prop_typec_power_role(chg, &pval);
		if (rc < 0) {
			dev_err(chg->dev, "Couldn't enable TYPEC rc=%d\n", rc);
			return rc;
		}
	}

	smblib_apsd_enable(chg, true);
	smblib_hvdcp_detect_enable(chg, false);

	rc = smblib_masked_write(chg, TYPE_C_CFG_REG,
				BC1P2_START_ON_CC_BIT, 0);
	if (rc < 0) {
		dev_err(chg->dev, "failed to write TYPE_C_CFG_REG rc=%d\n",
				rc);

		return rc;
	}

	/* Use simple write to clear interrupts */
	rc = smblib_write(chg, TYPE_C_INTERRUPT_EN_CFG_1_REG, 0);
	if (rc < 0) {
		dev_err(chg->dev,
			"Couldn't configure Type-C interrupts rc=%d\n", rc);
		return rc;
	}
#ifdef VENDOR_EDIT  /* zhangkun@BSP.CHG.Basic, 2019/02/22, Add for disable water detect*/
        val = chg->lpd_disabled ? 0 : TYPEC_WATER_DETECTION_INT_EN_BIT;
	/* Use simple write to enable only required interrupts */
	rc = smblib_write(chg, TYPE_C_INTERRUPT_EN_CFG_2_REG,
				TYPEC_SRC_BATT_HPWR_INT_EN_BIT | val);
#endif
	if (rc < 0) {
		dev_err(chg->dev,
			"Couldn't configure Type-C interrupts rc=%d\n", rc);
		return rc;
	}

	/* enable try.snk and clear force sink for DRP mode */
	rc = smblib_masked_write(chg, TYPE_C_MODE_CFG_REG,
				EN_TRY_SNK_BIT | EN_SNK_ONLY_BIT,
				EN_TRY_SNK_BIT);
	if (rc < 0) {
		dev_err(chg->dev,
			"Couldn't configure TYPE_C_MODE_CFG_REG rc=%d\n",
				rc);
		return rc;
	} else {
		chg->typec_try_mode |= EN_TRY_SNK_BIT;
	}

	/* For PD capable targets configure VCONN for software control */
	if (!chg->pd_not_supported) {
		rc = smblib_masked_write(chg, TYPE_C_VCONN_CONTROL_REG,
				 VCONN_EN_SRC_BIT | VCONN_EN_VALUE_BIT,
				 VCONN_EN_SRC_BIT);
		if (rc < 0) {
			dev_err(chg->dev,
				"Couldn't configure VCONN for SW control rc=%d\n",
				rc);
			return rc;
		}
	}

	/* Enable detection of unoriented debug accessory in source mode */
	rc = smblib_masked_write(chg, DEBUG_ACCESS_SRC_CFG_REG,
				 EN_UNORIENTED_DEBUG_ACCESS_SRC_BIT,
				 EN_UNORIENTED_DEBUG_ACCESS_SRC_BIT);
	if (rc < 0) {
		dev_err(chg->dev,
			"Couldn't configure TYPE_C_DEBUG_ACCESS_SRC_CFG_REG rc=%d\n",
				rc);
		return rc;
	}

	rc = smblib_masked_write(chg, USBIN_LOAD_CFG_REG,
		USBIN_IN_COLLAPSE_GF_SEL_MASK | USBIN_AICL_STEP_TIMING_SEL_MASK,
		0);
	if (rc < 0) {
		dev_err(chg->dev,
			"Couldn't set USBIN_LOAD_CFG_REG rc=%d\n", rc);
		return rc;
	}

	/* Set CC threshold to 1.6 V in source mode */
	rc = smblib_masked_write(chg, TYPE_C_EXIT_STATE_CFG_REG,
				SEL_SRC_UPPER_REF_BIT, SEL_SRC_UPPER_REF_BIT);
	if (rc < 0)
		dev_err(chg->dev,
			"Couldn't configure CC threshold voltage rc=%d\n", rc);

	return rc;
}

/* drivers/power/supply/qcom/qpnp-smb5.c:4256 */
static int smb5_determine_initial_status(struct smb5 *chip)
{
	struct smb_irq_data irq_data = {chip, "determine-initial-status"};
	struct smb_charger *chg = &chip->chg;
	union power_supply_propval val;
	int rc;

	rc = smblib_get_prop_usb_present(chg, &val);
	if (rc < 0) {
		pr_err("Couldn't get usb present rc=%d\n", rc);
		return rc;
	}
	chg->early_usb_attach = val.intval;

	if (chg->bms_psy)
		smblib_suspend_on_debug_battery(chg);

	usb_plugin_irq_handler(0, &irq_data);
	typec_attach_detach_irq_handler(0, &irq_data);
	typec_state_change_irq_handler(0, &irq_data);
	usb_source_change_irq_handler(0, &irq_data);
	chg_state_change_irq_handler(0, &irq_data);
	icl_change_irq_handler(0, &irq_data);
	batt_temp_changed_irq_handler(0, &irq_data);
	wdog_bark_irq_handler(0, &irq_data);
	typec_or_rid_detection_change_irq_handler(0, &irq_data);
	wdog_snarl_irq_handler(0, &irq_data);
#ifdef VENDOR_EDIT
/* Jianchao.Shi@BSP.CHG.Basic, 2018/07/13, sjc Add for fake typec */
    if (chg->early_usb_attach)
        schedule_delayed_work(&chg->typec_disable_cmd_work, msecs_to_jiffies(1000));
#endif

	return 0;
}

/* drivers/power/supply/qcom/qpnp-smb5.c:4570 */
static int smb5_request_interrupt(struct smb5 *chip,
				struct device_node *node, const char *irq_name)
{
	struct smb_charger *chg = &chip->chg;
	int rc, irq, irq_index;
	struct smb_irq_data *irq_data;

	irq = of_irq_get_byname(node, irq_name);
	if (irq < 0) {
		pr_err("Couldn't get irq %s byname\n", irq_name);
		return irq;
	}

	irq_index = smb5_get_irq_index_byname(irq_name);
	if (irq_index < 0) {
		pr_err("%s is not a defined irq\n", irq_name);
		return irq_index;
	}

	if (!smb5_irqs[irq_index].handler)
		return 0;

	irq_data = devm_kzalloc(chg->dev, sizeof(*irq_data), GFP_KERNEL);
	if (!irq_data)
		return -ENOMEM;

	irq_data->parent_data = chip;
	irq_data->name = irq_name;
	irq_data->storm_data = smb5_irqs[irq_index].storm_data;
	mutex_init(&irq_data->storm_data.storm_lock);

	smb5_irqs[irq_index].enabled = true;
	rc = devm_request_threaded_irq(chg->dev, irq, NULL,
					smb5_irqs[irq_index].handler,
					IRQF_ONESHOT, irq_name, irq_data);
	if (rc < 0) {
		pr_err("Couldn't request irq %d\n", irq);
		return rc;
	}

	smb5_irqs[irq_index].irq = irq;
	smb5_irqs[irq_index].irq_data = irq_data;
	if (smb5_irqs[irq_index].wake)
		enable_irq_wake(irq);

	return rc;
}

/* drivers/power/supply/qcom/qpnp-smb5.c:439 */
void smbchg_set_chargerid_switch_val(int value)
{
	struct oppo_chg_chip *chip = g_oppo_chip;
	
	if (chip->normalchg_gpio.chargerid_switch_gpio <= 0) {
		chg_err("chargerid_switch_gpio not exist, return\n");
		return;
	}

	if (IS_ERR_OR_NULL(chip->normalchg_gpio.pinctrl)
		|| IS_ERR_OR_NULL(chip->normalchg_gpio.chargerid_switch_active)
		|| IS_ERR_OR_NULL(chip->normalchg_gpio.chargerid_switch_sleep)
		|| IS_ERR_OR_NULL(chip->normalchg_gpio.chargerid_switch_default)) {
		chg_err("pinctrl null, return\n");
		return;
	}

	if (oppo_vooc_get_adapter_update_real_status() == ADAPTER_FW_NEED_UPDATE
		|| oppo_vooc_get_btb_temp_over() == true) {
		chg_err("adapter update or btb_temp_over, return\n");
		return;
	}
#if 0
	if (chip->pmic_spmi.not_support_1200ma && !value && !is_usb_present(chip)) {
	/* BugID 879716 : Solve some situatuion ChargerID is not 0 mV when usb is not present */
	// wenbin.liu@BSP.CHG.Basic, 2016/11/14
		chip->chargerid_volt = 0;
		chip->chargerid_volt_got = false;
	}
#endif
	mutex_lock(&chip->pmic_spmi.smb5_chip->chg.pinctrl_mutex);

	if (value) {
		gpio_direction_output(chip->normalchg_gpio.chargerid_switch_gpio, 1);
		pinctrl_select_state(chip->normalchg_gpio.pinctrl,
				chip->normalchg_gpio.chargerid_switch_default);
	} else {
		gpio_direction_output(chip->normalchg_gpio.chargerid_switch_gpio, 0);
		pinctrl_select_state(chip->normalchg_gpio.pinctrl,
				chip->normalchg_gpio.chargerid_switch_default);
	}

	mutex_unlock(&chip->pmic_spmi.smb5_chip->chg.pinctrl_mutex);
	chg_err("set value:%d, gpio_val:%d\n",
		value, gpio_get_value(chip->normalchg_gpio.chargerid_switch_gpio));
}

/* drivers/usb/phy/phy-msm-snps-hs.c:633 */
static int msm_hsphy_dpdm_regulator_enable(struct regulator_dev *rdev)
{
	int ret = 0;
	struct msm_hsphy *phy = rdev_get_drvdata(rdev);

	dev_dbg(phy->phy.dev, "%s dpdm_enable:%d\n",
				__func__, phy->dpdm_enable);

	mutex_lock(&phy->phy_lock);
	if (!phy->dpdm_enable) {
		ret = msm_hsphy_enable_power(phy, true);
		if (ret) {
			mutex_unlock(&phy->phy_lock);
			return ret;
		}

		msm_hsphy_enable_clocks(phy, true);
		msm_hsphy_reset(phy);

		/*
		 * For PMIC charger detection, place PHY in UTMI non-driving
		 * mode which leaves Dp and Dm lines in high-Z state.
		 */
		msm_usb_write_readback(phy->base, USB2_PHY_USB_PHY_HS_PHY_CTRL2,
					USB2_SUSPEND_N_SEL | USB2_SUSPEND_N,
					USB2_SUSPEND_N_SEL | USB2_SUSPEND_N);
		msm_usb_write_readback(phy->base, USB2_PHY_USB_PHY_UTMI_CTRL0,
					OPMODE_MASK, OPMODE_NONDRIVING);
		msm_usb_write_readback(phy->base, USB2_PHY_USB_PHY_CFG0,
					UTMI_PHY_DATAPATH_CTRL_OVERRIDE_EN,
					UTMI_PHY_DATAPATH_CTRL_OVERRIDE_EN);

		phy->dpdm_enable = true;
	}
	mutex_unlock(&phy->phy_lock);

	return ret;
}

/* drivers/usb/phy/phy-msm-snps-hs.c:672 */
static int msm_hsphy_dpdm_regulator_disable(struct regulator_dev *rdev)
{
	int ret = 0;
	struct msm_hsphy *phy = rdev_get_drvdata(rdev);

	dev_dbg(phy->phy.dev, "%s dpdm_enable:%d\n",
				__func__, phy->dpdm_enable);

	mutex_lock(&phy->phy_lock);
	if (phy->dpdm_enable) {
		if (!phy->cable_connected) {
			msm_hsphy_enable_clocks(phy, false);
			ret = msm_hsphy_enable_power(phy, false);
			if (ret < 0) {
				mutex_unlock(&phy->phy_lock);
				return ret;
			}
		}
		phy->dpdm_enable = false;
	}
	mutex_unlock(&phy->phy_lock);

	return ret;
}

/* drivers/usb/phy/phy-msm-snps-hs.c:697 */
static int msm_hsphy_dpdm_regulator_is_enabled(struct regulator_dev *rdev)
{
	struct msm_hsphy *phy = rdev_get_drvdata(rdev);

	dev_dbg(phy->phy.dev, "%s dpdm_enable:%d\n",
			__func__, phy->dpdm_enable);

	return phy->dpdm_enable;
}

/* drivers/usb/phy/phy-msm-snps-hs.c:713 */
static int msm_hsphy_regulator_init(struct msm_hsphy *phy)
{
	struct device *dev = phy->phy.dev;
	struct regulator_config cfg = {};
	struct regulator_init_data *init_data;

	init_data = devm_kzalloc(dev, sizeof(*init_data), GFP_KERNEL);
	if (!init_data)
		return -ENOMEM;

	init_data->constraints.valid_ops_mask |= REGULATOR_CHANGE_STATUS;
	phy->dpdm_rdesc.owner = THIS_MODULE;
	phy->dpdm_rdesc.type = REGULATOR_VOLTAGE;
	phy->dpdm_rdesc.ops = &msm_hsphy_dpdm_regulator_ops;
	phy->dpdm_rdesc.name = kbasename(dev->of_node->full_name);

	cfg.dev = dev;
	cfg.init_data = init_data;
	cfg.driver_data = phy;
	cfg.of_node = dev->of_node;

	phy->dpdm_rdev = devm_regulator_register(dev, &phy->dpdm_rdesc, &cfg);
	if (IS_ERR(phy->dpdm_rdev))
		return PTR_ERR(phy->dpdm_rdev);

	return 0;
}

/* drivers/usb/phy/phy-msm-snps-hs.c:427 */
static int msm_hsphy_init(struct usb_phy *uphy)
{
	struct msm_hsphy *phy = container_of(uphy, struct msm_hsphy, phy);
	int ret;
	u32 rcal_code = 0;

	dev_dbg(uphy->dev, "%s\n", __func__);

	ret = msm_hsphy_enable_power(phy, true);
	if (ret)
		return ret;

	msm_hsphy_enable_clocks(phy, true);
	msm_hsphy_reset(phy);

	msm_usb_write_readback(phy->base, USB2_PHY_USB_PHY_CFG0,
				UTMI_PHY_CMN_CTRL_OVERRIDE_EN,
				UTMI_PHY_CMN_CTRL_OVERRIDE_EN);

	msm_usb_write_readback(phy->base, USB2_PHY_USB_PHY_UTMI_CTRL5,
				POR, POR);

	msm_usb_write_readback(phy->base, USB2_PHY_USB_PHY_HS_PHY_CTRL_COMMON0,
				FSEL_MASK, 0);

	msm_usb_write_readback(phy->base, USB2_PHY_USB_PHY_HS_PHY_CTRL_COMMON1,
				PLLBTUNE, PLLBTUNE);

	msm_usb_write_readback(phy->base, USB2_PHY_USB_PHY_REFCLK_CTRL,
				REFCLK_SEL_MASK, REFCLK_SEL_DEFAULT);

	msm_usb_write_readback(phy->base, USB2_PHY_USB_PHY_HS_PHY_CTRL_COMMON1,
				VBUSVLDEXTSEL0, VBUSVLDEXTSEL0);

	msm_usb_write_readback(phy->base, USB2_PHY_USB_PHY_HS_PHY_CTRL1,
				VBUSVLDEXT0, VBUSVLDEXT0);

	/* set parameter ovrride  if needed */
	if (phy->param_override_seq)
		hsusb_phy_write_seq(phy->base, phy->param_override_seq,
				phy->param_override_seq_cnt, 0);

	if (phy->pre_emphasis) {
		u8 val = TXPREEMPAMPTUNE0(phy->pre_emphasis) &
				TXPREEMPAMPTUNE0_MASK;
		if (val)
			msm_usb_write_readback(phy->base,
				USB2PHY_USB_PHY_PARAMETER_OVERRIDE_X1,
				TXPREEMPAMPTUNE0_MASK, val);
	}

	if (phy->txvref_tune0) {
		u8 val = phy->txvref_tune0 & TXVREFTUNE0_MASK;

		msm_usb_write_readback(phy->base,
			USB2PHY_USB_PHY_PARAMETER_OVERRIDE_X1,
			TXVREFTUNE0_MASK, val);
	}

	if (phy->param_ovrd0) {
		msm_usb_write_readback(phy->base,
			USB2PHY_USB_PHY_PARAMETER_OVERRIDE_X0,
			PARAM_OVRD_MASK, phy->param_ovrd0);
	}

	if (phy->param_ovrd1) {
		msm_usb_write_readback(phy->base,
			USB2PHY_USB_PHY_PARAMETER_OVERRIDE_X1,
			PARAM_OVRD_MASK, phy->param_ovrd1);
	}

	if (phy->param_ovrd2) {
		msm_usb_write_readback(phy->base,
			USB2PHY_USB_PHY_PARAMETER_OVERRIDE_X2,
			PARAM_OVRD_MASK, phy->param_ovrd2);
	}

	if (phy->param_ovrd3) {
		msm_usb_write_readback(phy->base,
			USB2PHY_USB_PHY_PARAMETER_OVERRIDE_X3,
			PARAM_OVRD_MASK, phy->param_ovrd3);
	}

	dev_dbg(uphy->dev, "x0:%08x x1:%08x x2:%08x x3:%08x\n",
	readl_relaxed(phy->base + USB2PHY_USB_PHY_PARAMETER_OVERRIDE_X0),
	readl_relaxed(phy->base + USB2PHY_USB_PHY_PARAMETER_OVERRIDE_X1),
	readl_relaxed(phy->base + USB2PHY_USB_PHY_PARAMETER_OVERRIDE_X2),
	readl_relaxed(phy->base + USB2PHY_USB_PHY_PARAMETER_OVERRIDE_X3));

	if (phy->phy_rcal_reg) {
		rcal_code = readl_relaxed(phy->phy_rcal_reg) & phy->rcal_mask;

		dev_dbg(uphy->dev, "rcal_mask:%08x reg:%08x code:%08x\n",
				phy->rcal_mask, phy->phy_rcal_reg, rcal_code);
	}
#ifdef VENDOR_EDIT
/* tongfeng.Huang@BSP.CHG.Basic, 2018/02/11,  Add for USB */
	/*add for dynamic change tune settings*/
	/* If phy_tune1 modparam set, override tune1 value */
	if (dev_phy_tune1) {
		pr_err("%s():oppo (modparam) TUNE1 val:0x%02x\n", __func__, dev_phy_tune1);
		writel_relaxed(dev_phy_tune1, phy->base + QUSB2PHY_PORT_TUNE1);
	}
	/* If phy_tune2 modparam set, override tune2 value */
	if (dev_phy_tune2) {
		pr_err("%s():oppo (modparam) TUNE2 val:0x%02x\n", __func__, dev_phy_tune2);
		writel_relaxed(dev_phy_tune2, phy->base + QUSB2PHY_PORT_TUNE2);
	}
	/* If phy_tune3 modparam set, override tune3 value */
	if (dev_phy_tune3) {
		pr_err("%s():oppo (modparam) TUNE3 val:0x%02x\n", __func__, dev_phy_tune3);
		writel_relaxed(dev_phy_tune3, phy->base + QUSB2PHY_PORT_TUNE3);
	}
	/* If phy_tune4 modparam set, override tune4 value */
	if (dev_phy_tune4) {
		pr_err("%s():oppo (modparam) TUNE4 val:0x%02x\n", __func__, dev_phy_tune4);
		writel_relaxed(dev_phy_tune4, phy->base + QUSB2PHY_PORT_TUNE4);
	}
#endif /* VENDOR_EDIT */

	/* Use external resistor for tuning if efuse is not programmed */
	if (!rcal_code)
		msm_usb_write_readback(phy->base, USB2PHY_USB_PHY_RTUNE_SEL,
			RTUNE_SEL, RTUNE_SEL);

	msm_usb_write_readback(phy->base, USB2_PHY_USB_PHY_HS_PHY_CTRL_COMMON2,
				VREGBYPASS, VREGBYPASS);

	msm_usb_write_readback(phy->base, USB2_PHY_USB_PHY_HS_PHY_CTRL2,
				USB2_SUSPEND_N_SEL | USB2_SUSPEND_N,
				USB2_SUSPEND_N_SEL | USB2_SUSPEND_N);

	msm_usb_write_readback(phy->base, USB2_PHY_USB_PHY_UTMI_CTRL0,
				SLEEPM, SLEEPM);

	msm_usb_write_readback(phy->base, USB2_PHY_USB_PHY_UTMI_CTRL5,
				POR, 0);

	msm_usb_write_readback(phy->base, USB2_PHY_USB_PHY_HS_PHY_CTRL2,
				USB2_SUSPEND_N_SEL, 0);

	msm_usb_write_readback(phy->base, USB2_PHY_USB_PHY_CFG0,
				UTMI_PHY_CMN_CTRL_OVERRIDE_EN, 0);

#ifdef VENDOR_EDIT
	/* tongfeng.Huang@BSP.CHG.Basic, 2018/02/11,  Add for USB */
	hsusb_phy_read_seq(phy->base, phy->param_override_seq,
				phy->param_override_seq_cnt, 0);
	pr_debug("hsusb_phy_read_seq again  end\n");
#endif
	return 0;
}

/* drivers/usb/phy/phy-msm-snps-hs.c:580 */
static int msm_hsphy_set_suspend(struct usb_phy *uphy, int suspend)
{
	struct msm_hsphy *phy = container_of(uphy, struct msm_hsphy, phy);

	if (phy->suspended && suspend) {
		dev_dbg(uphy->dev, "%s: USB PHY is already suspended\n",
			__func__);
		return 0;
	}

	if (suspend) { /* Bus suspend */
		if (phy->cable_connected ||
			(phy->phy.flags & PHY_HOST_MODE)) {
			msm_hsphy_enable_clocks(phy, false);
		} else {/* Cable disconnect */
			mutex_lock(&phy->phy_lock);
			if (!phy->dpdm_enable) {
				msm_hsphy_enable_clocks(phy, false);
				msm_hsphy_enable_power(phy, false);
			} else {
				dev_dbg(uphy->dev, "dpdm reg still active.  Keep clocks/ldo ON\n");
			}
			mutex_unlock(&phy->phy_lock);
		}
		phy->suspended = true;
	} else { /* Bus resume and cable connect */
		msm_hsphy_enable_clocks(phy, true);
		phy->suspended = false;
	}

	return 0;
}

/* drivers/usb/dwc3/dwc3-msm.c:3495 */
static int dwc_dpdm_cb(struct notifier_block *nb, unsigned long evt, void *p)
{
	struct dwc3_msm *mdwc = container_of(nb, struct dwc3_msm, dpdm_nb);

	switch (evt) {
	case REGULATOR_EVENT_ENABLE:
		dev_dbg(mdwc->dev, "%s: enable state:%s\n", __func__,
				dwc3_drd_state_string(mdwc->drd_state));
		break;
	case REGULATOR_EVENT_DISABLE:
		dev_dbg(mdwc->dev, "%s: disable state:%s\n", __func__,
				dwc3_drd_state_string(mdwc->drd_state));
		if (mdwc->drd_state == DRD_STATE_UNDEFINED)
			schedule_delayed_work(&mdwc->sm_work, 0);
		break;
	default:
		dev_dbg(mdwc->dev, "%s: unknown event state:%s\n", __func__,
				dwc3_drd_state_string(mdwc->drd_state));
		break;
	}

	return NOTIFY_OK;
}
