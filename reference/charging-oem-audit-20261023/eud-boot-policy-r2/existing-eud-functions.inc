static int eud_probe(struct platform_device *pdev)
{
        struct eud_port *up;
        struct uart_port *port;
        struct resource *res;
        int ret;

        if (eud)
                return -EBUSY;

        up = devm_kzalloc(&pdev->dev, sizeof(*up), GFP_KERNEL);
        if (!up)
                return -ENOMEM;

        port = &up->port;
        port->membase = devm_platform_get_and_ioremap_resource(pdev, 0, &res);
        if (IS_ERR(port->membase))
                return PTR_ERR(port->membase);
        port->mapbase = res->start;

        /* This driver is bound only to qcom,sm8150-eud-com. The stock
         * dwc3-msm driver uses 0x11 for one read/write wait state; RX41
         * verifies it enables native FIFO advancement on this board.
         */
        up->ahb2phy_cfg = devm_ioremap(&pdev->dev, EUD_AHB2PHY_TOP_CFG,
                                     sizeof(u32));
        if (!up->ahb2phy_cfg)
                return -ENOMEM;
        up->original_ahb2phy_cfg = readl(up->ahb2phy_cfg);
        writel(EUD_AHB2PHY_ONE_WAIT, up->ahb2phy_cfg);
        if (readl(up->ahb2phy_cfg) != EUD_AHB2PHY_ONE_WAIT) {
                eud_restore_ahb2phy(up);
                return dev_err_probe(&pdev->dev, -EIO,
                                     "AHB2PHY one-wait readback failed\n");
        }
        dev_info(&pdev->dev, "AHB2PHY TOP_CFG=%08x original=%08x\n",
                 EUD_AHB2PHY_ONE_WAIT, up->original_ahb2phy_cfg);

        port->dev      = &pdev->dev;
        port->iotype   = UPIO_MEM;
        port->flags    = UPF_BOOT_AUTOCONF | UPF_SKIP_TEST;
        port->ops      = &eud_ops;
        port->fifosize = 7;
        port->type     = EUD_PORT_TYPE;
        port->line     = 0;
        port->uartclk  = 115200;
        spin_lock_init(&port->lock);
	mutex_init(&up->tx_mutex);

        /* the EDK2 boot chain leaves EUD enabled; enable it if it did not */
        writel_relaxed(1, port->membase + EUD_REG_CSR_EUD_EN);

        INIT_WORK(&up->tx_work, eud_tx_work);
        INIT_DELAYED_WORK(&up->rx_work, eud_rx_work);

        ret = uart_add_one_port(&eud_uart_driver, port);
        if (ret) {
                eud_restore_ahb2phy(up);
                return ret;
        }

        platform_set_drvdata(pdev, port);
        eud = up;

        ret = eud_rx_request_irq(pdev, up);
        if (ret) {
                up->rx_irq_fault = EUD_IRQ_FAULT_SETUP;
                dev_warn(&pdev->dev, "RX46 IRQ unavailable: %d; polling retained\n", ret);
        }

        if (strstr(saved_command_line, "console=eud")) {
                register_console(&eud_console);
                up->console_registered = true;
        }

        /* let the boot log burst drain before the RX work starts talking */
        schedule_delayed_work(&up->rx_work, msecs_to_jiffies(20000));

        dev_info(&pdev->dev,
                 "EUD COM ready: ttyEUD0, [0x%02x][1,3..14]=tty [2]=bootloader\n",
                 EUD_RX_UART_ID);
        return 0;
}

static void eud_reboot_cmd(struct eud_port *up, unsigned int len)
{
	unsigned long flags;
	const char *what;

	if (eud_reboot_pending)
		return;
	if (len == 2)
		what = "bootloader";
	else
		return;
	eud_reboot_pending = true;

	uart_port_lock_irqsave(&up->port, &flags);
	up->rx_stopping = true;
	eud_rx_irq_stop_locked(up, 0);
	uart_port_unlock_irqrestore(&up->port, flags);
	if (up->rx_irq_requested)
		synchronize_irq(up->rx_irq);

	pr_info("eud: reboot2 %s requested\n", what);
	/*
	 * The F1 notice is queued by RX work. With nbcon, printk returning
	 * does not mean its frames have reached the FIFO. Drain the queued
	 * records before retiring the printer and giving the PHY back to ABL.
	 * Do not hold tx_mutex while waiting for the printer that needs it.
	 */
	pr_flush(1000, true);
	if (up->console_registered) {
		unregister_console(&eud_console);
		up->console_registered = false;
	}

	/* Serialize the last TTY writer with hardware shutdown as well. */
	mutex_lock(&up->tx_mutex);
	uart_port_lock_irqsave(&up->port, &flags);
	up->tx_stopping = true;
	uart_port_unlock_irqrestore(&up->port, flags);
	eud_restore_ahb2phy(up);
	writel(0, up->port.membase + EUD_REG_CSR_EUD_EN);
	readl(up->port.membase + EUD_REG_CSR_EUD_EN);
	mutex_unlock(&up->tx_mutex);
	kernel_restart((char *)what);
}
