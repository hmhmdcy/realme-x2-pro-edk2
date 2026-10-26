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

static int msm_hsphy_dpdm_regulator_is_enabled(struct regulator_dev *rdev)
{
	struct msm_hsphy *phy = rdev_get_drvdata(rdev);

	dev_dbg(phy->phy.dev, "%s dpdm_enable:%d\n",
			__func__, phy->dpdm_enable);

	return phy->dpdm_enable;
}
