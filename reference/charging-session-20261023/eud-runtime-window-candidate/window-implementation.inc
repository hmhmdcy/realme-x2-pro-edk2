/* Internal COM software window. eud_window_lock also serializes pointer
 * lifetime with probe/remove and both PM paths. No inter-driver calls here.
 */
static DEFINE_MUTEX(eud_window_lock);
static u64 eud_window_sequence;
static u64 eud_window_orphan;

static void eud_window_result(struct eud_port *up,
                              struct eud_com_window_result *result, int error)
{
        *result = (struct eud_com_window_result) {
                .cookie = up ? up->window_cookie : 0,
                .state = up ? up->window_state : EUD_COM_REMOVED,
                .software_quiet = up && up->window_quiet,
                .cancelled = up && up->window_state == EUD_COM_CANCELLED,
                .error = error,
        };
}

int eud_com_quiet_begin(struct eud_com_window_result *result)
{
        struct eud_port *up;
        unsigned long flags;
        int ret = 0;

        if (!result)
                return -EINVAL;
        mutex_lock(&eud_window_lock);
        up = eud;
        if (!up) {
                ret = -ENODEV;
                goto out;
        }
        if (current_work() == &up->rx_work.work ||
            current_work() == &up->tx_work) {
                ret = -EDEADLK;
                goto out;
        }
        uart_port_lock_irqsave(&up->port, &flags);
        if (up->window_quiet || up->window_state != EUD_COM_ACTIVE)
                ret = -EBUSY;
        else if (up->window_system_pm || up->window_runtime_pm)
                ret = -EHOSTDOWN;
        else if (up->tx_stopping || up->rx_stopping || eud_reboot_pending ||
                 up->rx_bootloader_pending)
                ret = -ESHUTDOWN;
        else if (!up->rx_irq_started)
                ret = -EAGAIN; /* Do not reinterpret probe's delayed startup. */
        if (ret) {
                uart_port_unlock_irqrestore(&up->port, flags);
                goto out;
        }
        /* Never reuse a token, including after an unbind/reprobe. */
        if (++eud_window_sequence == 0)
                ++eud_window_sequence;
        up->window_cookie = eud_window_sequence;
        up->window_state = EUD_COM_QUIETING;
        up->window_quiet = true;
        up->window_irq_enabled = up->rx_irq_enabled;
        up->rx_irq_waiting = false;
        up->rx_console_irq_credit = false;
        if (up->rx_irq_enabled) {
                up->rx_irq_enabled = false;
                disable_irq_nosync(up->rx_irq);
        }
        uart_port_unlock_irqrestore(&up->port, flags);

        if (up->rx_irq_requested)
                synchronize_irq(up->rx_irq);
        cancel_delayed_work_sync(&up->rx_work);
        cancel_work_sync(&up->tx_work);
        /* Do not hold this mutex while joining RX: command/reboot dispatch
         * may print. Atomic console callbacks are fenced by the UART gate.
         */
        mutex_lock(&up->tx_mutex);
        mutex_unlock(&up->tx_mutex);
        uart_port_lock_irqsave(&up->port, &flags);
        up->window_state = EUD_COM_QUIET;
        uart_port_unlock_irqrestore(&up->port, flags);
out:
        eud_window_result(up, result, ret);
        if (ret)
                result->cookie = 0;
        mutex_unlock(&eud_window_lock);
        return ret;
}

int eud_com_quiet_cancel(u64 cookie, struct eud_com_window_result *result)
{
        struct eud_port *up;
        unsigned long flags;
        int ret = 0;

        if (!result)
                return -EINVAL;
        mutex_lock(&eud_window_lock);
        up = eud;
        if (!up)
                ret = -ENODEV;
        else if (!cookie || cookie != up->window_cookie || !up->window_quiet)
                ret = -ESTALE;
        else {
                uart_port_lock_irqsave(&up->port, &flags);
                up->window_state = EUD_COM_CANCELLED;
                uart_port_unlock_irqrestore(&up->port, flags);
        }
        eud_window_result(up, result, ret ? ret : -ECANCELED);
        if (ret)
                result->cookie = cookie;
        mutex_unlock(&eud_window_lock);
        return ret;
}

int eud_com_quiet_end(u64 cookie, struct eud_com_window_result *result)
{
        struct eud_port *up;
        unsigned long flags;
        bool cancelled = false;
        int ret = 0;

        if (!result)
                return -EINVAL;
        mutex_lock(&eud_window_lock);
        up = eud;
        if (!up) {
                /* The removed borrower finishes its other components first.
                 * Only its exact end token releases the reprobe interlock.
                 */
                cancelled = cookie && cookie == eud_window_orphan;
                if (cancelled)
                        eud_window_orphan = 0;
                ret = -ENODEV;
                goto out;
        }
        uart_port_lock_irqsave(&up->port, &flags);
        if (!cookie || cookie != up->window_cookie || !up->window_quiet)
                ret = -ESTALE;
        else if (up->window_system_pm || up->window_runtime_pm ||
                 up->rx_stopping || up->tx_stopping || eud_reboot_pending ||
                 up->rx_bootloader_pending)
                ret = -ESHUTDOWN;
        else if (up->window_irq_enabled && !up->rx_irq_requested)
                ret = -ENXIO;
        if (ret) {
                uart_port_unlock_irqrestore(&up->port, flags);
                goto out;
        }
        cancelled = up->window_state == EUD_COM_CANCELLED;
        up->window_quiet = false;
        up->window_state = EUD_COM_ACTIVE;
        if (up->window_irq_enabled) {
                up->rx_irq_enabled = true;
                enable_irq(up->rx_irq);
        }
        /* Do not reset an old fault, rearm a disabled diagnostic IRQ, or
         * restore its old watchdog timestamp after the pause.
         */
        if (up->port.state && !uart_tx_stopped(&up->port) &&
            kfifo_len(&up->port.state->port.xmit_fifo))
                schedule_work(&up->tx_work);
        schedule_delayed_work(&up->rx_work,
                              msecs_to_jiffies(EUD_RX_POLL_MS));
        uart_port_unlock_irqrestore(&up->port, flags);
out:
        eud_window_result(up, result, ret ? ret : cancelled ? -ECANCELED : 0);
        result->restored = !ret;
        result->cancelled = cancelled;
        result->restore_error = ret;
        result->cookie = cookie;
        mutex_unlock(&eud_window_lock);
        return ret;
}

static int eud_window_prepare(struct device *dev)
{
        struct uart_port *port;
        struct eud_port *up;
        int ret = 0;

        mutex_lock(&eud_window_lock);
        port = dev_get_drvdata(dev);
        if (port) {
                up = to_eud_port(port);
                if (up->window_quiet)
                        ret = -EBUSY;
                else
                        up->window_system_pm = true;
        }
        mutex_unlock(&eud_window_lock);
        return ret;
}

static void eud_window_complete(struct device *dev)
{
        struct uart_port *port;

        mutex_lock(&eud_window_lock);
        port = dev_get_drvdata(dev);
        if (port)
                to_eud_port(port)->window_system_pm = false;
        mutex_unlock(&eud_window_lock);
}

static int eud_window_runtime_suspend(struct device *dev)
{
        struct uart_port *port;
        struct eud_port *up;
        int ret = 0;

        mutex_lock(&eud_window_lock);
        port = dev_get_drvdata(dev);
        if (port) {
                up = to_eud_port(port);
                if (up->window_quiet)
                        ret = -EBUSY;
                else
                        up->window_runtime_pm = true;
        }
        mutex_unlock(&eud_window_lock);
        return ret;
}

static int eud_window_runtime_resume(struct device *dev)
{
        struct uart_port *port;

        mutex_lock(&eud_window_lock);
        port = dev_get_drvdata(dev);
        if (port)
                to_eud_port(port)->window_runtime_pm = false;
        mutex_unlock(&eud_window_lock);
        return 0;
}

static const struct dev_pm_ops eud_window_pm_ops = {
        .prepare = eud_window_prepare,
        .complete = eud_window_complete,
        .runtime_suspend = eud_window_runtime_suspend,
        .runtime_resume = eud_window_runtime_resume,
};
