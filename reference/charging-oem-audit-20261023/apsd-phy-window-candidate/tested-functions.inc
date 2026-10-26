static const struct phy_ops qcom_snps_hsphy_gen_ops;
static const u32 qcom_snps_hsphy_window_offsets[] = {
	USB2_PHY_USB_PHY_HS_PHY_CTRL2,
	USB2_PHY_USB_PHY_UTMI_CTRL0,
	USB2_PHY_USB_PHY_CFG0,
};
static const u32 qcom_snps_hsphy_window_masks[] = {
	USB2_SUSPEND_N_SEL | USB2_SUSPEND_N,
	OPMODE_MASK,
	UTMI_PHY_DATAPATH_CTRL_OVERRIDE_EN,
};
static const u32 qcom_snps_hsphy_window_values[] = {
	USB2_SUSPEND_N_SEL | USB2_SUSPEND_N,
	OPMODE_NONDRIVING,
	UTMI_PHY_DATAPATH_CTRL_OVERRIDE_EN,
};

static bool qcom_snps_hsphy_window_busy(struct qcom_snps_hsphy *hsphy)
{
	return hsphy->window.state != QCOM_HSPHY_WINDOW_IDLE;
}

static int qcom_snps_hsphy_window_write(struct qcom_snps_hsphy *hsphy,
				      u32 offset, u32 mask, u32 value)
{
	u32 actual;

	lockdep_assert_held(&hsphy->phy->mutex);
	actual = readl_relaxed(hsphy->base + offset);
	writel_relaxed((actual & ~mask) | (value & mask), hsphy->base + offset);
	actual = readl_relaxed(hsphy->base + offset);
	return (actual & mask) == (value & mask) ? 0 : -EIO;
}

int qcom_snps_hsphy_window_begin(struct phy *phy,
		struct qcom_snps_hsphy_window_result *result)
{
	struct qcom_snps_hsphy_window_result *window;
	struct qcom_snps_hsphy *hsphy;
	int i, ret;

	if (!result)
		return -EINVAL;
	memset(result, 0, sizeof(*result));
	if (!phy || phy->ops != &qcom_snps_hsphy_gen_ops)
		return -ENODEV;
	hsphy = phy_get_drvdata(phy);
	/* Never resume to gain a detection window; PM operations are outside
	 * the generic PHY mutex, including all failure/ref-release paths. */
	ret = pm_runtime_get_if_active(hsphy->dev);
	if (ret <= 0)
		return ret < 0 ? ret : -EAGAIN;
	mutex_lock(&phy->mutex);
	window = &hsphy->window;
	if (qcom_snps_hsphy_window_busy(hsphy))
		ret = -EBUSY;
	else if (!hsphy->phy_initialized || phy->init_count <= 0)
		ret = -EAGAIN;
	else if (hsphy->mode != PHY_MODE_USB_DEVICE)
		ret = -EOPNOTSUPP;
	else {
		memset(window, 0, sizeof(*window));
		if (!++hsphy->window_generation)
			++hsphy->window_generation;
		window->cookie = hsphy->window_generation;
		window->state = QCOM_HSPHY_WINDOW_CLAIMED;
		hsphy->window_pm_ref = true;
		/* Capture all originals before any write, including when entering
		 * later fails part-way. Never synthesize normal/default values. */
		for (i = 0; i < ARRAY_SIZE(qcom_snps_hsphy_window_offsets); i++)
			window->saved[i] = readl_relaxed(hsphy->base +
				qcom_snps_hsphy_window_offsets[i]) & qcom_snps_hsphy_window_masks[i];
		for (i = 0; i < ARRAY_SIZE(qcom_snps_hsphy_window_offsets); i++) {
			window->attempted |= BIT(i);
			ret = qcom_snps_hsphy_window_write(hsphy,
				qcom_snps_hsphy_window_offsets[i],
				qcom_snps_hsphy_window_masks[i], qcom_snps_hsphy_window_values[i]);
			if (ret)
				break;
			window->verified |= BIT(i);
		}
		window->enter_error = ret;
		window->high_z = !ret;
		window->state = ret ? QCOM_HSPHY_WINDOW_FAILED : QCOM_HSPHY_WINDOW_HIGH_Z;
		*result = *window;
		mutex_unlock(&phy->mutex);
		return ret;
	}
	mutex_unlock(&phy->mutex);
	pm_runtime_put_noidle(hsphy->dev);
	return ret;
}

int qcom_snps_hsphy_window_end(struct phy *phy, u64 cookie,
		struct qcom_snps_hsphy_window_result *result)
{
	struct qcom_snps_hsphy_window_result *window;
	struct qcom_snps_hsphy *hsphy;
	int i, ret = 0;

	if (!result)
		return -EINVAL;
	memset(result, 0, sizeof(*result));
	if (!phy || phy->ops != &qcom_snps_hsphy_gen_ops)
		return -ENODEV;
	hsphy = phy_get_drvdata(phy);
	mutex_lock(&phy->mutex);
	window = &hsphy->window;
	if (!cookie || cookie != window->cookie || !qcom_snps_hsphy_window_busy(hsphy)) {
		ret = -ESTALE;
		goto unlock;
	}
	/* exit/set_mode/runtime callbacks cannot invalidate this snapshot. */
	if (!hsphy->phy_initialized || phy->init_count <= 0 || !hsphy->window_pm_ref) {
		ret = -ESHUTDOWN;
		goto failed;
	}
	window->high_z = false;
	window->restored_mask = 0;
	for (i = ARRAY_SIZE(qcom_snps_hsphy_window_offsets) - 1; i >= 0; i--) {
		ret = qcom_snps_hsphy_window_write(hsphy,
			qcom_snps_hsphy_window_offsets[i],
			qcom_snps_hsphy_window_masks[i], window->saved[i]);
		if (ret)
			goto failed;
		window->restored_mask |= BIT(i);
	}
	window->restored = true;
	window->restore_error = 0;
	window->state = QCOM_HSPHY_WINDOW_IDLE;
	hsphy->window_pm_ref = false;
	*result = *window;
	mutex_unlock(&phy->mutex);
	pm_runtime_mark_last_busy(hsphy->dev);
	pm_runtime_put_autosuspend(hsphy->dev);
	return 0;
failed:
	window->high_z = false;
	window->restore_error = ret;
	window->state = QCOM_HSPHY_WINDOW_FAILED;
	*result = *window;
unlock:
	mutex_unlock(&phy->mutex);
	return ret;
}

static inline void qcom_snps_hsphy_write_mask(void __iomem *base, u32 offset,
						u32 mask, u32 val)
{
	u32 reg;

	reg = readl_relaxed(base + offset);
	reg &= ~mask;
	reg |= val & mask;
	writel_relaxed(reg, base + offset);

	/* Ensure above write is completed */
	readl_relaxed(base + offset);
}

static int qcom_snps_hsphy_suspend(struct qcom_snps_hsphy *hsphy)
{
	dev_dbg(&hsphy->phy->dev, "Suspend QCOM SNPS PHY\n");

	if (hsphy->mode == PHY_MODE_USB_HOST) {
		/* Enable auto-resume to meet remote wakeup timing */
		qcom_snps_hsphy_write_mask(hsphy->base,
					   USB2_PHY_USB_PHY_HS_PHY_CTRL2,
					   USB2_AUTO_RESUME,
					   USB2_AUTO_RESUME);
		usleep_range(500, 1000);
		qcom_snps_hsphy_write_mask(hsphy->base,
					   USB2_PHY_USB_PHY_HS_PHY_CTRL2,
					   0, USB2_AUTO_RESUME);
	}

	return 0;
}

static int qcom_snps_hsphy_resume(struct qcom_snps_hsphy *hsphy)
{
	dev_dbg(&hsphy->phy->dev, "Resume QCOM SNPS PHY, mode\n");

	return 0;
}

static int __maybe_unused qcom_snps_hsphy_runtime_suspend(struct device *dev)
{
	struct qcom_snps_hsphy *hsphy = dev_get_drvdata(dev);
	int ret = 0;

	mutex_lock(&hsphy->phy->mutex);
	if (qcom_snps_hsphy_window_busy(hsphy))
		ret = -EBUSY;
	else if (hsphy->phy_initialized)
		ret = qcom_snps_hsphy_suspend(hsphy);
	mutex_unlock(&hsphy->phy->mutex);
	return ret;
}

static int __maybe_unused qcom_snps_hsphy_runtime_resume(struct device *dev)
{
	struct qcom_snps_hsphy *hsphy = dev_get_drvdata(dev);
	int ret = 0;

	mutex_lock(&hsphy->phy->mutex);
	if (qcom_snps_hsphy_window_busy(hsphy))
		ret = -EBUSY;
	else if (hsphy->phy_initialized)
		ret = qcom_snps_hsphy_resume(hsphy);
	mutex_unlock(&hsphy->phy->mutex);
	return ret;
}

static int qcom_snps_hsphy_set_mode(struct phy *phy, enum phy_mode mode,
				    int submode)
{
	struct qcom_snps_hsphy *hsphy = phy_get_drvdata(phy);

	if (qcom_snps_hsphy_window_busy(hsphy))
		return -EBUSY;

	hsphy->mode = mode;
	return 0;
}

static int qcom_snps_hsphy_init(struct phy *phy)
{
	struct qcom_snps_hsphy *hsphy = phy_get_drvdata(phy);
	int ret, i;

	if (qcom_snps_hsphy_window_busy(hsphy))
		return -EBUSY;

	dev_vdbg(&phy->dev, "%s(): Initializing SNPS HS phy\n", __func__);

	ret = regulator_bulk_enable(ARRAY_SIZE(hsphy->vregs), hsphy->vregs);
	if (ret)
		return ret;

	ret = clk_bulk_prepare_enable(hsphy->num_clks, hsphy->clks);
	if (ret) {
		dev_err(&phy->dev, "failed to enable clocks, %d\n", ret);
		goto poweroff_phy;
	}

	ret = reset_control_assert(hsphy->phy_reset);
	if (ret) {
		dev_err(&phy->dev, "failed to assert phy_reset, %d\n", ret);
		goto disable_clks;
	}

	usleep_range(100, 150);

	ret = reset_control_deassert(hsphy->phy_reset);
	if (ret) {
		dev_err(&phy->dev, "failed to de-assert phy_reset, %d\n", ret);
		goto disable_clks;
	}

	qcom_snps_hsphy_write_mask(hsphy->base, USB2_PHY_USB_PHY_CFG0,
					UTMI_PHY_CMN_CTRL_OVERRIDE_EN,
					UTMI_PHY_CMN_CTRL_OVERRIDE_EN);
	qcom_snps_hsphy_write_mask(hsphy->base, USB2_PHY_USB_PHY_UTMI_CTRL5,
							POR, POR);
	qcom_snps_hsphy_write_mask(hsphy->base,
					USB2_PHY_USB_PHY_HS_PHY_CTRL_COMMON0,
					FSEL_MASK, 0);
	qcom_snps_hsphy_write_mask(hsphy->base,
					USB2_PHY_USB_PHY_HS_PHY_CTRL_COMMON1,
					PLLBTUNE, PLLBTUNE);
	qcom_snps_hsphy_write_mask(hsphy->base, USB2_PHY_USB_PHY_REFCLK_CTRL,
					REFCLK_SEL_DEFAULT, REFCLK_SEL_MASK);
	qcom_snps_hsphy_write_mask(hsphy->base,
					USB2_PHY_USB_PHY_HS_PHY_CTRL_COMMON1,
					VBUSVLDEXTSEL0, VBUSVLDEXTSEL0);
	qcom_snps_hsphy_write_mask(hsphy->base, USB2_PHY_USB_PHY_HS_PHY_CTRL1,
					VBUSVLDEXT0, VBUSVLDEXT0);

	for (i = 0; i < ARRAY_SIZE(hsphy->update_seq_cfg); i++) {
		if (hsphy->update_seq_cfg[i].need_update)
			qcom_snps_hsphy_write_mask(hsphy->base,
					hsphy->update_seq_cfg[i].offset,
					hsphy->update_seq_cfg[i].mask,
					hsphy->update_seq_cfg[i].value);
	}

	qcom_snps_hsphy_write_mask(hsphy->base,
					USB2_PHY_USB_PHY_HS_PHY_CTRL_COMMON2,
					VREGBYPASS, VREGBYPASS);

	qcom_snps_hsphy_write_mask(hsphy->base, USB2_PHY_USB_PHY_HS_PHY_CTRL2,
					USB2_SUSPEND_N_SEL | USB2_SUSPEND_N,
					USB2_SUSPEND_N_SEL | USB2_SUSPEND_N);

	qcom_snps_hsphy_write_mask(hsphy->base, USB2_PHY_USB_PHY_UTMI_CTRL0,
					SLEEPM, SLEEPM);

	qcom_snps_hsphy_write_mask(hsphy->base, USB2_PHY_USB_PHY_HS_PHY_CTRL_COMMON0,
				   SIDDQ, 0);

	qcom_snps_hsphy_write_mask(hsphy->base, USB2_PHY_USB_PHY_UTMI_CTRL5,
					POR, 0);

	qcom_snps_hsphy_write_mask(hsphy->base, USB2_PHY_USB_PHY_HS_PHY_CTRL2,
					USB2_SUSPEND_N_SEL, 0);

	qcom_snps_hsphy_write_mask(hsphy->base, USB2_PHY_USB_PHY_CFG0,
					UTMI_PHY_CMN_CTRL_OVERRIDE_EN, 0);

	hsphy->phy_initialized = true;

	return 0;

disable_clks:
	clk_bulk_disable_unprepare(hsphy->num_clks, hsphy->clks);
poweroff_phy:
	regulator_bulk_disable(ARRAY_SIZE(hsphy->vregs), hsphy->vregs);

	return ret;
}

static int qcom_snps_hsphy_exit(struct phy *phy)
{
	struct qcom_snps_hsphy *hsphy = phy_get_drvdata(phy);

	if (qcom_snps_hsphy_window_busy(hsphy))
		return -EBUSY;

	reset_control_assert(hsphy->phy_reset);
	clk_bulk_disable_unprepare(hsphy->num_clks, hsphy->clks);
	regulator_bulk_disable(ARRAY_SIZE(hsphy->vregs), hsphy->vregs);
	hsphy->phy_initialized = false;

	return 0;
}

int phy_init(struct phy *phy)
{
	int ret;

	if (!phy)
		return 0;

	ret = phy_pm_runtime_get_sync(phy);
	if (ret < 0 && ret != -ENOTSUPP)
		return ret;
	ret = 0; /* Override possible ret == -ENOTSUPP */

	mutex_lock(&phy->mutex);
	if (phy->power_count > phy->init_count)
		dev_warn(&phy->dev, "phy_power_on was called before phy_init\n");

	if (phy->init_count == 0 && phy->ops->init) {
		ret = phy->ops->init(phy);
		if (ret < 0) {
			dev_err(&phy->dev, "phy init failed --> %d\n", ret);
			goto out;
		}
	}
	++phy->init_count;

out:
	mutex_unlock(&phy->mutex);
	phy_pm_runtime_put(phy);
	return ret;
}

int phy_exit(struct phy *phy)
{
	int ret;

	if (!phy)
		return 0;

	ret = phy_pm_runtime_get_sync(phy);
	if (ret < 0 && ret != -ENOTSUPP)
		return ret;
	ret = 0; /* Override possible ret == -ENOTSUPP */

	mutex_lock(&phy->mutex);
	if (phy->init_count == 1 && phy->ops->exit) {
		ret = phy->ops->exit(phy);
		if (ret < 0) {
			dev_err(&phy->dev, "phy exit failed --> %d\n", ret);
			goto out;
		}
	}
	--phy->init_count;

out:
	mutex_unlock(&phy->mutex);
	phy_pm_runtime_put(phy);
	return ret;
}

int phy_set_mode_ext(struct phy *phy, enum phy_mode mode, int submode)
{
	int ret = 0;

	if (!phy)
		return 0;

	mutex_lock(&phy->mutex);
	if (phy->ops->set_mode)
		ret = phy->ops->set_mode(phy, mode, submode);
	if (!ret)
		phy->attrs.mode = mode;
	mutex_unlock(&phy->mutex);

	return ret;
}
