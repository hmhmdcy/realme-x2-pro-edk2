static void eud_console_device_lock(struct console *co, unsigned long *flags)
{
	mutex_lock(&eud->tx_mutex);
	migrate_disable();
	*flags = 0;
}

static void eud_console_device_unlock(struct console *co, unsigned long flags)
{
	migrate_enable();
	mutex_unlock(&eud->tx_mutex);
}

static void eud_console_write_thread(struct console *co,
				     struct nbcon_write_context *wctxt)
{
	struct eud_port *up = eud;
	unsigned int offset = 0;
	bool kick = false, collect = true;

	while (offset < wctxt->len) {
		unsigned long flags;
		unsigned int n;
		bool owned;
		int ret;

		uart_port_lock_irqsave(&up->port, &flags);
		if (!nbcon_enter_unsafe(wctxt)) {
			uart_port_unlock_irqrestore(&up->port, flags);
			break;
		}

		if (!offset) {
			ret = eud_console_rx_locked(up);
			kick = ret != 0;
			collect = ret >= 0;
		}

		n = min_t(unsigned int, wctxt->len - offset, EUD_TX_CHUNK);
		eud_send_frame(&up->port, (const u8 *)wctxt->outbuf + offset,
			       n, EUD_TX_SOURCE_CONSOLE);
		offset += n;
		if (collect) {
			ret = eud_console_rx_locked(up);
			kick |= ret != 0;
			collect = ret >= 0;
		}

		owned = nbcon_exit_unsafe(wctxt);
		uart_port_unlock_irqrestore(&up->port, flags);
		if (!owned)
			break;
		cond_resched();
	}

	if (kick && !READ_ONCE(up->rx_stopping) &&
            !READ_ONCE(up->window_quiet))
		mod_delayed_work(system_percpu_wq, &up->rx_work, 0);
}

static void eud_console_write_atomic(struct console *co,
				     struct nbcon_write_context *wctxt)
{
	if (!nbcon_enter_unsafe(wctxt))
		return;
	eud_console_write_legacy(co, wctxt->outbuf, wctxt->len);
	nbcon_exit_unsafe(wctxt);
}
