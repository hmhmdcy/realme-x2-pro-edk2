static int dwc3_gadget_recover_locked(struct dwc3 *dwc);

static inline bool dwc3_gadget_window_busy(struct dwc3 *dwc)
{
	enum dwc3_gadget_window_state state = READ_ONCE(dwc->detect_window.state);

	return state != DWC3_WINDOW_IDLE && state != DWC3_WINDOW_SHUTDOWN;
}

static bool dwc3_gadget_window_wanted(struct dwc3 *dwc)
{
	unsigned long flags;
	bool wanted;

	/* softconnect is a bit-field; read it under the same lock as pullup. */
	spin_lock_irqsave(&dwc->lock, flags);
	wanted = dwc->softconnect;
	spin_unlock_irqrestore(&dwc->lock, flags);
	return wanted;
}

static void dwc3_gadget_window_result_locked(struct dwc3 *dwc,
		struct dwc3_gadget_window_result *result)
{
	struct dwc3_gadget_window *window = &dwc->detect_window;

	*result = (struct dwc3_gadget_window_result) {
		.cookie = window->cookie,
		.state = window->state,
		.halted = window->halted,
		.cancelled = window->cancelled,
		.restore_wanted = dwc->softconnect,
		.halt_error = window->halt_error,
		.restore_error = window->restore_error,
	};
}

static int dwc3_gadget_window_park_locked(struct dwc3 *dwc)
{
	struct dwc3_gadget_window *window = &dwc->detect_window;
	int ret;

	lockdep_assert_held(&dwc->connect_mutex);
	ret = dwc3_gadget_soft_disconnect(dwc);
	if (!ret && !(dwc3_readl(dwc, DWC3_DSTS) & DWC3_DSTS_DEVCTRLHLT))
		ret = -EIO;
	window->halt_error = ret;
	window->halted = !ret;
	return ret;
}

int dwc3_gadget_window_begin(struct dwc3 *dwc,
		struct dwc3_gadget_window_result *result)
{
	struct dwc3_gadget_window *window = &dwc->detect_window;
	unsigned long flags;
	int ret;

	if (!result)
		return -EINVAL;
	memset(result, 0, sizeof(*result));
	/* No connect_mutex is held across any PM operation. This API does not
	 * invoke resume, so it cannot obtain its quiet state through PHY reset.
	 */
	ret = pm_runtime_get_if_active(dwc->dev);
	if (ret <= 0)
		return ret < 0 ? ret : -EAGAIN;

	spin_lock_irqsave(&dwc->lock, flags);
	if (dwc->detect_stopping || !dwc->gadget_driver)
		ret = -ESHUTDOWN;
	else if (dwc->dr_mode != USB_DR_MODE_PERIPHERAL ||
		 dwc->current_dr_role != DWC3_GCTL_PRTCAP_DEVICE)
		ret = -EOPNOTSUPP;
	else if (dwc->err_state != DWC3_ERR_NONE)
		ret = -EIO;
	else if (window->state != DWC3_WINDOW_IDLE || dwc->detect_pm_busy ||
		 dwc->detect_system_blocked)
		ret = -EBUSY;
	else {
		memset(window, 0, sizeof(*window));
		if (!++dwc->detect_generation)
			++dwc->detect_generation;
		window->cookie = dwc->detect_generation;
		window->state = DWC3_WINDOW_CLAIMED;
		window->pm_ref = true;
		ret = 0;
	}
	spin_unlock_irqrestore(&dwc->lock, flags);
	if (ret) {
		pm_runtime_put_noidle(dwc->dev);
		return ret;
	}

	mutex_lock(&dwc->connect_mutex);
	/* UDC stop/removal sets stopping before waiting for connect_mutex. */
	if (READ_ONCE(dwc->detect_stopping)) {
		ret = -ESHUTDOWN;
	} else {
		synchronize_irq(dwc->irq_gadget);
		ret = dwc3_gadget_window_park_locked(dwc);
	}
	spin_lock_irqsave(&dwc->lock, flags);
	/* shutdown may have obtained connect_mutex first after the claim. */
	if (window->state != DWC3_WINDOW_SHUTDOWN) {
		window->state = ret ? DWC3_WINDOW_FAILED : DWC3_WINDOW_HALTED;
		if (ret && !window->halt_error)
			window->halt_error = ret;
	}
	dwc3_gadget_window_result_locked(dwc, result);
	spin_unlock_irqrestore(&dwc->lock, flags);
	mutex_unlock(&dwc->connect_mutex);
	return ret;
}

int dwc3_gadget_window_cancel(struct dwc3 *dwc, u64 cookie,
		struct dwc3_gadget_window_result *result)
{
	struct dwc3_gadget_window *window = &dwc->detect_window;
	unsigned long flags;
	int ret;

	if (!result)
		return -EINVAL;
	memset(result, 0, sizeof(*result));
	mutex_lock(&dwc->connect_mutex);
	if (!cookie || cookie != window->cookie ||
	    window->state == DWC3_WINDOW_IDLE ||
	    READ_ONCE(dwc->detect_stopping)) {
		ret = -ESTALE;
		goto unlock;
	}
	ret = dwc3_gadget_window_park_locked(dwc);
	spin_lock_irqsave(&dwc->lock, flags);
	window->cancelled = true;
	window->state = ret ? DWC3_WINDOW_FAILED : DWC3_WINDOW_HALTED;
	dwc3_gadget_window_result_locked(dwc, result);
	spin_unlock_irqrestore(&dwc->lock, flags);
unlock:
	mutex_unlock(&dwc->connect_mutex);
	return ret;
}

int dwc3_gadget_window_end(struct dwc3 *dwc, u64 cookie,
		struct dwc3_gadget_window_result *result)
{
	struct dwc3_gadget_window *window = &dwc->detect_window;
	unsigned long flags;
	bool wanted;
	int attempt, ret = 0;

	if (!result)
		return -EINVAL;
	memset(result, 0, sizeof(*result));
	mutex_lock(&dwc->connect_mutex);
	if (!cookie || cookie != window->cookie ||
	    window->state == DWC3_WINDOW_IDLE ||
	    READ_ONCE(dwc->detect_stopping)) {
		ret = -ESTALE;
		goto unlock;
	}
	spin_lock_irqsave(&dwc->lock, flags);
	window->state = DWC3_WINDOW_RESTORING;
	spin_unlock_irqrestore(&dwc->lock, flags);

	for (attempt = 0; attempt < 2; attempt++) {
		wanted = dwc3_gadget_window_wanted(dwc);
		if (window->recovery_pending) {
			ret = dwc3_gadget_recover_locked(dwc);
			if (!ret && !wanted)
				ret = dwc3_gadget_window_park_locked(dwc);
			if (!ret)
				window->recovery_pending = false;
		} else if (wanted) {
			synchronize_irq(dwc->irq_gadget);
			ret = dwc3_gadget_soft_connect(dwc);
		} else {
			ret = dwc3_gadget_window_park_locked(dwc);
		}
		if (ret)
			break;
		spin_lock_irqsave(&dwc->lock, flags);
		if (wanted == dwc->softconnect && !dwc->detect_stopping) {
			window->halted = !wanted;
			window->restore_error = 0;
			window->state = DWC3_WINDOW_IDLE;
			window->pm_ref = false;
			dwc3_gadget_window_result_locked(dwc, result);
			spin_unlock_irqrestore(&dwc->lock, flags);
			mutex_unlock(&dwc->connect_mutex);
			pm_runtime_mark_last_busy(dwc->dev);
			pm_runtime_put_autosuspend(dwc->dev);
			return 0;
		}
		spin_unlock_irqrestore(&dwc->lock, flags);
	}
	if (!ret)
		ret = -EAGAIN;
	/* Never turn a failed reconnect into a claimed quiet success. */
	window->restore_error = ret;
	dwc3_gadget_window_park_locked(dwc);
	spin_lock_irqsave(&dwc->lock, flags);
	window->state = DWC3_WINDOW_FAILED;
	dwc3_gadget_window_result_locked(dwc, result);
	spin_unlock_irqrestore(&dwc->lock, flags);
unlock:
	mutex_unlock(&dwc->connect_mutex);
	return ret;
}

static void dwc3_gadget_window_shutdown(struct dwc3 *dwc)
{
	struct dwc3_gadget_window *window = &dwc->detect_window;
	unsigned long flags;
	bool put;

	spin_lock_irqsave(&dwc->lock, flags);
	dwc->detect_stopping = true;
	spin_unlock_irqrestore(&dwc->lock, flags);
	mutex_lock(&dwc->connect_mutex);
	put = window->pm_ref;
	if (put) {
		window->cancelled = true;
		dwc3_gadget_window_park_locked(dwc);
	}
	spin_lock_irqsave(&dwc->lock, flags);
	window->state = DWC3_WINDOW_SHUTDOWN;
	window->pm_ref = false;
	dwc->softconnect = false;
	spin_unlock_irqrestore(&dwc->lock, flags);
	mutex_unlock(&dwc->connect_mutex);
	if (put)
		pm_runtime_put_noidle(dwc->dev);
}

static int dwc3_gadget_pullup(struct usb_gadget *g, int is_on)
{
	struct dwc3		*dwc = gadget_to_dwc(g);
	int			ret;
	unsigned long		flags;

	is_on = !!is_on;

	spin_lock_irqsave(&dwc->lock, flags);
	if (dwc->detect_stopping) {
		spin_unlock_irqrestore(&dwc->lock, flags);
		return -ESHUTDOWN;
	}
	dwc->softconnect = is_on;
	if (dwc3_gadget_window_busy(dwc)) {
		spin_unlock_irqrestore(&dwc->lock, flags);
		return 0; /* intent only; the explicit end reconciles it */
	}
	spin_unlock_irqrestore(&dwc->lock, flags);

	/*
	 * Avoid issuing a runtime resume if the device is already in the
	 * suspended state during gadget disconnect.  DWC3 gadget was already
	 * halted/stopped during runtime suspend.
	 */
	if (!is_on) {
		pm_runtime_barrier(dwc->dev);
		if (pm_runtime_suspended(dwc->dev))
			return 0;
	}

	/*
	 * Check the return value for successful resume, or error.  For a
	 * successful resume, the DWC3 runtime PM resume routine will handle
	 * the run stop sequence, so avoid duplicate operations here.
	 */
	ret = pm_runtime_get_sync(dwc->dev);
	if (!ret || ret < 0) {
		pm_runtime_put(dwc->dev);
		if (ret < 0)
			pm_runtime_set_suspended(dwc->dev);
		return ret;
	}

	if (dwc->pullups_connected == is_on) {
		pm_runtime_put(dwc->dev);
		return 0;
	}

	synchronize_irq(dwc->irq_gadget);

	/* Serialize against dwc3_err_recovery_work() */
	mutex_lock(&dwc->connect_mutex);
	/* begin may have claimed after this pullup's PM/IRQ preparation. */
	if (dwc3_gadget_window_busy(dwc) || READ_ONCE(dwc->detect_stopping)) {
		mutex_unlock(&dwc->connect_mutex);
		pm_runtime_put(dwc->dev);
		return 0;
	}
	is_on = dwc3_gadget_window_wanted(dwc);
	if (!is_on)
		ret = dwc3_gadget_soft_disconnect(dwc);
	else
		ret = dwc3_gadget_soft_connect(dwc);
	mutex_unlock(&dwc->connect_mutex);

	pm_runtime_put(dwc->dev);

	return ret;
}

static int dwc3_gadget_recover_locked(struct dwc3 *dwc)
{
	unsigned long flags;
	int ret;

	lockdep_assert_held(&dwc->connect_mutex);
	ret = dwc3_gadget_soft_disconnect(dwc);
	dwc3_disconnect_gadget_sleepable(dwc);
	if (ret)
		goto failed;
	if (dwc3_gadget_window_wanted(dwc)) {
		u32 count;

		synchronize_irq(dwc->irq_gadget);
		spin_lock_irqsave(&dwc->lock, flags);
		count = ++dwc->err_recovery_count;
		spin_unlock_irqrestore(&dwc->lock, flags);
		if (count > DWC3_ERR_RECOVERY_MAX) {
			ret = -EIO;
			goto failed;
		}
		ret = dwc3_gadget_soft_connect(dwc);
		if (ret)
			goto failed;
	}
	spin_lock_irqsave(&dwc->lock, flags);
	dwc->err_state = DWC3_ERR_NONE;
	spin_unlock_irqrestore(&dwc->lock, flags);
	return 0;
failed:
	dev_err(dwc->dev, "Unable to recover the controller\n");
	spin_lock_irqsave(&dwc->lock, flags);
	dwc->err_state = DWC3_ERR_UNRECOVERABLE;
	spin_unlock_irqrestore(&dwc->lock, flags);
	return ret;
}

static void dwc3_err_recovery_work(struct work_struct *work)
{
	struct dwc3 *dwc = container_of(work, struct dwc3, err_recovery_work);

	mutex_lock(&dwc->connect_mutex);
	if (!READ_ONCE(dwc->detect_stopping)) {
		if (dwc3_gadget_window_busy(dwc))
			dwc->detect_window.recovery_pending = true;
		else
			dwc3_gadget_recover_locked(dwc);
	}
	mutex_unlock(&dwc->connect_mutex);
}

int dwc3_gadget_suspend(struct dwc3 *dwc)
{
	int ret;

	if (dwc3_gadget_window_busy(dwc))
		return -EBUSY;

	ret = dwc3_gadget_soft_disconnect(dwc);
	/*
	 * Attempt to reset the controller's state. Likely no
	 * communication can be established until the host
	 * performs a port reset.
	 */
	if (ret && dwc->softconnect) {
		dwc3_gadget_soft_connect(dwc);
		return -EAGAIN;
	}

	dwc3_disconnect_gadget_sleepable(dwc);

	return 0;
}

int dwc3_gadget_resume(struct dwc3 *dwc)
{
	if (dwc3_gadget_window_busy(dwc))
		return -EBUSY;

	if (!dwc->gadget_driver || !dwc->softconnect)
		return 0;

	return dwc3_gadget_soft_connect(dwc);
}

static int dwc3_gadget_start(struct usb_gadget *g,
		struct usb_gadget_driver *driver)
{
	struct dwc3		*dwc = gadget_to_dwc(g);
	unsigned long		flags;
	int			ret;
	int			irq;

	irq = dwc->irq_gadget;
	ret = request_threaded_irq(irq, dwc3_interrupt, dwc3_thread_interrupt,
			IRQF_SHARED, "dwc3", dwc->ev_buf);
	if (ret) {
		dev_err(dwc->dev, "failed to request irq #%d --> %d\n",
				irq, ret);
		return ret;
	}

	spin_lock_irqsave(&dwc->lock, flags);
	memset(&dwc->detect_window, 0, sizeof(dwc->detect_window));
	dwc->detect_stopping = false;
	dwc->gadget_driver	= driver;
	spin_unlock_irqrestore(&dwc->lock, flags);

	if (dwc->sys_wakeup)
		device_wakeup_enable(dwc->sysdev);

	return 0;
}

static int dwc3_gadget_stop(struct usb_gadget *g)
{
	struct dwc3		*dwc = gadget_to_dwc(g);
	unsigned long		flags;

	dwc3_gadget_window_shutdown(dwc);

	if (dwc->sys_wakeup)
		device_wakeup_disable(dwc->sysdev);

	spin_lock_irqsave(&dwc->lock, flags);
	dwc->gadget_driver	= NULL;
	dwc->max_cfg_eps = 0;
	spin_unlock_irqrestore(&dwc->lock, flags);

	free_irq(dwc->irq_gadget, dwc->ev_buf);

	return 0;
}

void dwc3_gadget_exit(struct dwc3 *dwc)
{
	if (!dwc->gadget)
		return;

	dwc3_gadget_window_shutdown(dwc);
	dwc3_enable_susphy(dwc, true);
	usb_del_gadget(dwc->gadget);
	cancel_work_sync(&dwc->err_recovery_work);
	mutex_destroy(&dwc->connect_mutex);
	dwc3_gadget_free_endpoints(dwc);
	usb_put_gadget(dwc->gadget);
	dma_free_coherent(dwc->sysdev, DWC3_BOUNCE_SIZE, dwc->bounce,
			  dwc->bounce_addr);
	kfree(dwc->setup_buf);
	dma_free_coherent(dwc->sysdev, sizeof(*dwc->ep0_trb) * 2,
			  dwc->ep0_trb, dwc->ep0_trb_addr);
}

static int dwc3_gadget_window_pm_enter(struct dwc3 *dwc)
{
	unsigned long flags;
	int ret = 0;

	spin_lock_irqsave(&dwc->lock, flags);
	if (dwc3_gadget_window_busy(dwc) || dwc->detect_pm_busy)
		ret = -EBUSY;
	else
		dwc->detect_pm_busy = true;
	spin_unlock_irqrestore(&dwc->lock, flags);
	return ret;
}

static void dwc3_gadget_window_pm_exit(struct dwc3 *dwc)
{
	unsigned long flags;

	spin_lock_irqsave(&dwc->lock, flags);
	dwc->detect_pm_busy = false;
	spin_unlock_irqrestore(&dwc->lock, flags);
}

int dwc3_pm_prepare(struct dwc3 *dwc)
{
	struct device *dev = dwc->dev;
	unsigned long flags;
	int ret = 0;

	spin_lock_irqsave(&dwc->lock, flags);
	if (dwc3_gadget_window_busy(dwc) || dwc->detect_pm_busy)
		ret = -EBUSY;
	else
		dwc->detect_system_blocked = true;
	spin_unlock_irqrestore(&dwc->lock, flags);
	if (ret)
		return ret;

	/*
	 * Indicate to the PM core that it may safely leave the device in
	 * runtime suspend if runtime-suspended already in device mode.
	 */
	if (dwc->current_dr_role == DWC3_GCTL_PRTCAP_DEVICE &&
	    pm_runtime_suspended(dev) &&
	    !dev_pinctrl(dev))
		return 1;

	return 0;
}

void dwc3_pm_complete(struct dwc3 *dwc)
{
	u32		reg;
	unsigned long flags;

	spin_lock_irqsave(&dwc->lock, flags);
	dwc->detect_system_blocked = false;
	spin_unlock_irqrestore(&dwc->lock, flags);

	if (dwc->current_dr_role == DWC3_GCTL_PRTCAP_HOST &&
			dwc->dis_split_quirk) {
		reg = dwc3_readl(dwc, DWC3_GUCTL3);
		reg |= DWC3_GUCTL3_SPLITDISABLE;
		dwc3_writel(dwc, DWC3_GUCTL3, reg);
	}
}
