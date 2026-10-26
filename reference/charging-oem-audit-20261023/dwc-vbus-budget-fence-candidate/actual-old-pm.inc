int old_dwc3_pm_suspend(struct dwc3 *dwc)
{
	struct device *dev = dwc->dev;
	int		ret;

	ret = dwc3_suspend_common(dwc, PMSG_SUSPEND);
	if (ret)
		return ret;

	pinctrl_pm_select_sleep_state(dev);

	return 0;
}

int old_dwc3_pm_resume(struct dwc3 *dwc)
{
	struct device *dev = dwc->dev;
	int		ret = 0;

	pinctrl_pm_select_default_state(dev);

	pm_runtime_disable(dev);
	ret = pm_runtime_set_active(dev);
	if (ret)
		goto out;

	ret = dwc3_resume_common(dwc, PMSG_RESUME);
	if (ret)
		pm_runtime_set_suspended(dev);

out:
	pm_runtime_enable(dev);

	return ret;
}
