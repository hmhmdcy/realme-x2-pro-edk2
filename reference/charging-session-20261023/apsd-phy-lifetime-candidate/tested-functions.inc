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

static int qcom_snps_hsphy_window_begin_active(struct phy *phy,
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

static int qcom_snps_hsphy_window_end_active(struct phy *phy, u64 cookie,
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
#include "phy-lifetime.inc"
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

	ret = window_provider_quiesce(hsphy, QCOM_HSPHY_WINDOW_RUNTIME, false);
	if (ret)
		return ret;
	mutex_lock(&hsphy->phy->mutex);
	if (hsphy->window_dead) {
		mutex_unlock(&hsphy->phy->mutex);
		return -ESHUTDOWN;
	}
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
	if (hsphy->window_dead) {
		mutex_unlock(&hsphy->phy->mutex);
		return -ESHUTDOWN;
	}
	if (qcom_snps_hsphy_window_busy(hsphy))
		ret = -EBUSY;
	else if (hsphy->phy_initialized)
		ret = qcom_snps_hsphy_resume(hsphy);
	mutex_unlock(&hsphy->phy->mutex);
	if (!ret)
		window_provider_complete(hsphy, QCOM_HSPHY_WINDOW_RUNTIME);
	return ret;
}

static int qcom_snps_hsphy_set_mode(struct phy *phy, enum phy_mode mode,
				    int submode)
{
	struct qcom_snps_hsphy *hsphy = phy_get_drvdata(phy);

	if (hsphy->window_dead)
		return -ESHUTDOWN;
	if (qcom_snps_hsphy_window_busy(hsphy))
		return -EBUSY;

	hsphy->mode = mode;
	return 0;
}

static int qcom_snps_hsphy_init(struct phy *phy)
{
	struct qcom_snps_hsphy *hsphy = phy_get_drvdata(phy);
	int ret, i;

	if (hsphy->window_dead)
		return -ESHUTDOWN;
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

	if (hsphy->window_dead)
		return -ESHUTDOWN;
	if (qcom_snps_hsphy_window_busy(hsphy))
		return -EBUSY;

	reset_control_assert(hsphy->phy_reset);
	clk_bulk_disable_unprepare(hsphy->num_clks, hsphy->clks);
	regulator_bulk_disable(ARRAY_SIZE(hsphy->vregs), hsphy->vregs);
	hsphy->phy_initialized = false;

	return 0;
}

static int qcom_snps_hsphy_prepare(struct device *dev)
{
 return window_provider_quiesce(dev_get_drvdata(dev), QCOM_HSPHY_WINDOW_SYSTEM, false);
}

static void qcom_snps_hsphy_complete(struct device *dev)
{
 window_provider_complete(dev_get_drvdata(dev), QCOM_HSPHY_WINDOW_SYSTEM);
}

static void qcom_snps_hsphy_withdraw(void *data)
{
 struct qcom_snps_hsphy *h = data;
 int ret;

 window_provider_disable_pm(h);
 ret = window_provider_quiesce(h, QCOM_HSPHY_WINDOW_REMOVE, true);
 if (ret)
  dev_err(h->dev, "PHY withdrawal without restored state: %d\n", ret);
}

static void qcom_snps_hsphy_remove(struct platform_device *pdev)
{
 qcom_snps_hsphy_withdraw(platform_get_drvdata(pdev));
}

static void qcom_snps_hsphy_shutdown(struct platform_device *pdev)
{
 struct qcom_snps_hsphy *h = platform_get_drvdata(pdev);
 int ret;

 window_provider_disable_pm(h);
 ret = window_provider_quiesce(h, QCOM_HSPHY_WINDOW_SHUTDOWN, true);
 if (ret)
  dev_err(h->dev, "PHY shutdown without restored state: %d\n", ret);
}

static int qcom_snps_hsphy_probe(struct platform_device *pdev)
{
	struct device *dev = &pdev->dev;
	struct qcom_snps_hsphy *hsphy;
	struct phy_provider *phy_provider;
	struct phy *generic_phy;
	int ret, i;
	int num;

	hsphy = devm_kzalloc(dev, sizeof(*hsphy), GFP_KERNEL);
	if (!hsphy)
		return -ENOMEM;

	hsphy->dev = dev;
	window_provider_init(hsphy);

	hsphy->base = devm_platform_ioremap_resource(pdev, 0);
	if (IS_ERR(hsphy->base))
		return PTR_ERR(hsphy->base);

	ret = qcom_snps_hsphy_clk_init(hsphy);
	if (ret)
		return dev_err_probe(dev, ret, "failed to initialize clocks\n");

	hsphy->phy_reset = devm_reset_control_get_exclusive(&pdev->dev, NULL);
	if (IS_ERR(hsphy->phy_reset)) {
		dev_err(dev, "failed to get phy core reset\n");
		return PTR_ERR(hsphy->phy_reset);
	}

	num = ARRAY_SIZE(hsphy->vregs);
	for (i = 0; i < num; i++)
		hsphy->vregs[i].supply = qcom_snps_hsphy_vreg_names[i];

	ret = devm_regulator_bulk_get(dev, num, hsphy->vregs);
	if (ret)
		return dev_err_probe(dev, ret,
				     "failed to get regulator supplies\n");

	/*
	 * Enable runtime PM before creating the PHY, phy_create() only enables
	 * it on the PHY device if already enabled on the parent. Hold a usage
	 * reference so callbacks cannot run before the PHY is ready.
	 */
	pm_runtime_get_noresume(dev);
	pm_runtime_set_active(dev);
 /* Same enable/managed cleanup as devm_pm_runtime_enable; the final
  * withdrawal must disable/join platform PM BEFORE generic PHY devres. */
 pm_runtime_enable(dev);
 ret = devm_add_action_or_reset(dev, window_provider_pm_cleanup, hsphy);
	if (ret) {
		pm_runtime_put_noidle(dev);
		return ret;
	}
	/*
	 * Prevent runtime pm from being ON by default. Users can enable
	 * it using power/control in sysfs.
	 */
	pm_runtime_forbid(dev);

	generic_phy = devm_phy_create(dev, NULL, &qcom_snps_hsphy_gen_ops);
	if (IS_ERR(generic_phy)) {
		ret = PTR_ERR(generic_phy);
		dev_err(dev, "failed to create phy, %d\n", ret);
		pm_runtime_put_noidle(dev);
		return ret;
	}
	hsphy->phy = generic_phy;

	dev_set_drvdata(dev, hsphy);
	phy_set_drvdata(generic_phy, hsphy);
	qcom_snps_hsphy_read_override_param_seq(dev);

	phy_provider = devm_of_phy_provider_register(dev, of_phy_simple_xlate);
	if (IS_ERR(phy_provider)) {
		pm_runtime_put_noidle(dev);
		return PTR_ERR(phy_provider);
	}

 ret = window_provider_publish(hsphy);
 if (ret) {
  pm_runtime_put_noidle(dev);
  return ret;
 }
 /* LAST devres action: runs BEFORE provider, generic PHY, PM, reset, clocks,
  * regulators and MMIO are released. Also closes every post-publication
  * probe failure; add_action_or_reset calls withdrawal on allocation error. */
 ret = devm_add_action_or_reset(dev, qcom_snps_hsphy_withdraw, hsphy);
 if (ret) {
  pm_runtime_put_noidle(dev);
  return ret;
 }
	dev_dbg(dev, "Registered Qcom-SNPS HS phy\n");
	pm_runtime_put(dev);

	return 0;
}
