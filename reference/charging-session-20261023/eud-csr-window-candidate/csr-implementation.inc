/* Optional CSR stage. The software quiet owner must separately keep the
 * actual MMIO power/lifecycle valid; this COM binding has no such resource.
 * No component/PM callback is invoked while holding eud_window_lock.
 */
static int eud_csr_validate_locked(struct eud_port *up, u64 cookie, bool enter)
{
        unsigned long flags;
        int ret = 0;

        if (!up)
                return -ENODEV;
        if (!cookie || cookie != up->window_cookie || !up->window_quiet)
                return -ESTALE;
        if (current_work() == &up->rx_work.work ||
            current_work() == &up->tx_work)
                return -EDEADLK;
        uart_port_lock_irqsave(&up->port, &flags);
        if (up->window_system_pm || up->window_runtime_pm)
                ret = -EHOSTDOWN;
        else if (up->tx_stopping || up->rx_stopping || eud_reboot_pending ||
                 up->rx_bootloader_pending)
                ret = -ESHUTDOWN;
        else if (up->window_state != EUD_COM_QUIET &&
                 up->window_state != EUD_COM_CANCELLED)
                ret = -EBUSY;
        else if (enter && up->window_state == EUD_COM_CANCELLED)
                ret = -ECANCELED;
        uart_port_unlock_irqrestore(&up->port, flags);
        return ret;
}

static void eud_csr_result_locked(struct eud_port *up, u64 cookie,
                                  struct eud_com_csr_result *result, int error)
{
        *result = (struct eud_com_csr_result) { .cookie = cookie };
        if (up && cookie && cookie == up->window_cookie && up->window_quiet) {
                *result = up->window_csr;
                result->software_quiet = true;
                result->cancelled = up->window_state == EUD_COM_CANCELLED;
        } else if (!up && cookie && cookie == eud_csr_orphan.cookie) {
                *result = eud_csr_orphan;
        }
        result->cookie = cookie;
        result->error = error;
        if (!up) {
                result->removed = true;
                result->restored = false;
        }
}

int eud_com_csr_begin(u64 cookie, struct eud_com_csr_result *result)
{
        struct eud_port *up;
        u32 value;
        int ret;

        if (!result)
                return -EINVAL;
        mutex_lock(&eud_window_lock);
        up = eud;
        ret = eud_csr_validate_locked(up, cookie, true);
        if (ret)
                goto out;
        if (up->window_csr.hardware_owned || up->window_csr.saved_valid) {
                ret = -EALREADY;
                goto out;
        }
        value = readl(up->port.membase + EUD_REG_CSR_EUD_EN);
        up->window_csr.readback = value;
        up->window_csr.readback_valid = true;
        if (value != 0 && value != 1) {
                ret = -EOPNOTSUPP;
                if (!up->window_csr.enter_error)
                        up->window_csr.enter_error = ret;
                goto out;
        }
        up->window_csr.saved_value = value;
        up->window_csr.saved_valid = true;
        /* Acquire before any write: failed readback must retain ownership. */
        up->window_csr.hardware_owned = true;
        if (value) {
                up->window_csr.csr_touched = true;
                writel(0, up->port.membase + EUD_REG_CSR_EUD_EN);
                value = readl(up->port.membase + EUD_REG_CSR_EUD_EN);
                up->window_csr.readback = value;
        }
        up->window_csr.disabled_verified = value == 0;
        ret = value == 0 ? 0 : -EIO;
        if (ret && !up->window_csr.enter_error)
                up->window_csr.enter_error = ret;
out:
        eud_csr_result_locked(up, cookie, result, ret);
        mutex_unlock(&eud_window_lock);
        return ret;
}

int eud_com_csr_restore(u64 cookie, struct eud_com_csr_result *result)
{
        struct eud_port *up;
        u32 value;
        int ret;

        if (!result)
                return -EINVAL;
        mutex_lock(&eud_window_lock);
        up = eud;
        ret = eud_csr_validate_locked(up, cookie, false);
        if (ret)
                goto out;
        if (!up->window_csr.hardware_owned || !up->window_csr.saved_valid) {
                ret = -EALREADY;
                goto out;
        }
        value = readl(up->port.membase + EUD_REG_CSR_EUD_EN);
        if (value != up->window_csr.saved_value) {
                up->window_csr.csr_touched = true;
                writel(up->window_csr.saved_value,
                       up->port.membase + EUD_REG_CSR_EUD_EN);
                value = readl(up->port.membase + EUD_REG_CSR_EUD_EN);
        }
        up->window_csr.readback = value;
        up->window_csr.readback_valid = true;
        up->window_csr.disabled_verified = value == 0;
        ret = value == up->window_csr.saved_value ? 0 : -EIO;
        if (ret) {
                if (!up->window_csr.restore_error)
                        up->window_csr.restore_error = ret;
        } else {
                up->window_csr.hardware_owned = false;
                up->window_csr.restored = true;
        }
out:
        eud_csr_result_locked(up, cookie, result, ret);
        mutex_unlock(&eud_window_lock);
        return ret;
}
