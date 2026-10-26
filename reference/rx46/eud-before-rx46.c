// SPDX-License-Identifier: GPL-2.0-only
/*
 * Qualcomm EUD COM: console, tty and command channel (realme X2 Pro).
 *
 * EUD presents a small register FIFO that a host PC sees as a serial port.  On
 * this board (RMX1931 / samurai) the MTP UART is not wired, so this FIFO is the
 * only console there is.  Everything below was measured on hardware; handover
 * sections 21 and 29 hold the raw evidence.
 *
 *  - TX: one register write is one FIFO entry: ID (0x90), LEN, then one entry
 *    per data byte.  The FIFO is about seven entries deep and INT_STATUS_1
 *    BIT(1) reads back stuck-at-set on this unit, so the only flow control that
 *    works is timing: 200 us per register write, 2 ms per frame.  Faster than
 *    that and whole frames are dropped, which loses four bytes out of the
 *    middle of a log line.
 *  - RX: id 0x90 carries tty payload of length 1 or 3..14; length 2 remains
 *    the header-only bootloader command. SM8150 SOUTH AHB2PHY TOP_CFG must
 *    be set to 0x11 before consecutive DAT reads. Session 41 verifies native
 *    ABC/DEFG in UEFI across reboot and in Linux. Collect the whole frame
 *    under the TX lock before printk or tty delivery; interleaved TX corrupts
 *    unread data. The host still needs receipt/retry for unaccepted OUTs.
 *  - COM fields occupy the low byte. Upper lanes may reflect different
 *    entries as the FIFO advances; mask with 0xff, never unpack four bytes.
 *  - The console is registered only when the command line asks for it: this
 *    firmware uses "earlycon=eud,... console=eud" without keep_bootcon, so the
 *    real console retires the early writer. FIFO accesses share the port lock.
 */

#include <linux/circ_buf.h>
#include <linux/console.h>
#include <linux/delay.h>
#include <linux/device.h>
#include <linux/init.h>
#include <linux/io.h>
#include <linux/kfifo.h>
#include <linux/kernel.h>
#include <linux/minmax.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/platform_device.h>
#include <linux/serial_core.h>
#include <linux/slab.h>
#include <linux/tty.h>
#include <linux/tty_flip.h>
#include <linux/workqueue.h>
#include <linux/reboot.h>

/* offsets inside the 0x2000 register window */
#define EUD_REG_COM_TX_ID      0x0000
#define EUD_REG_COM_TX_LEN     0x0004
#define EUD_REG_COM_TX_DAT     0x0008
#define EUD_REG_COM_RX_ID      0x000C
#define EUD_REG_COM_RX_LEN     0x0010
#define EUD_REG_COM_RX_DAT     0x0014
#define EUD_REG_INT0_EN_MASK   0x0020
#define EUD_REG_INT1_EN_MASK   0x0024
#define EUD_REG_INT_STATUS_0   0x0040
#define EUD_REG_INT_STATUS_1   0x0044
#define EUD_REG_CSR_EUD_EN     0x1014

/* SM8150 SOUTH SWMAN, confirmed by the stock RMX1931 DAL map. */
#define EUD_AHB2PHY_TOP_CFG    0x088ee010
#define EUD_AHB2PHY_ONE_WAIT   0x11

#define EUD_COM_UART_ID        0x90    /* the id this port transmits with */
#define EUD_TX_CHUNK           4u      /* data bytes per frame: six entries */
#define EUD_TX_BYTE_US         200
#define EUD_TX_FRAME_US        2000

#define EUD_RX_POLL_MS         20
#define EUD_RX_MAX_FRAME       14    /* MAX_FIFO_SIZE in kernel/msm */
#define EUD_RX_UART_ID         0x90    /* upstream UART_ID: the channel */
#define EUD_RX_CMD_ID          0x81    /* APPS exec-env: our command channel */
#define EUD_RX_CHAR_ID         0x82    /* payload is tty input */
#define EUD_RX_CHAR_ID2        0x83    /* alternate id for the next char */
#define EUD_INT_RX_PENDING     BIT(0)  /* INT_STATUS_1: RX data available */
#define EUD_INT_RX             BIT(0)  /* INT_STATUS_1: RX data pending */
#define EUD_RX_REPORTS         40      /* bounded diagnostic verbosity */

/* one FIFO entry is consumed per poll; the id byte selects the state */
#define EUD_RX_STATE_IDLE      0
#define EUD_RX_STATE_CHAR      1
#define EUD_RX_STATE_CMD       2

#define EUD_PORT_TYPE          124     /* PORT_EUD; no UAPI number assigned */

struct eud_port {
        struct uart_port port;
        struct work_struct tx_work;
        struct delayed_work rx_work;
        u32 rx_polls;
        u32 rx_reports;
        u32 rx_last_status;
        u32 rx_last_id;
        u32 rx_last_len;
        u32 rx_last_after;
        u32 rx_pending;
        u32 rx_bad_headers;
        u32 rx_frames;
        u32 rx_f1;
        u32 rx_bytes;
        u32 rx_tty_bytes;
        u32 rx_no_tty;
        u32 rx_bad_id;
        u32 rx_bad_len;
        u8  rx_state;   /* EUD_RX_STATE: idle / expect char / expect cmd */
        u8  rx_collect; /* collecting a payload right now */
        u8  rx_have;    /* payload bytes collected so far */
        u8  rx_len;     /* payload bytes this message should have */
        u8  rx_id;      /* id of the message being collected */
        u8  rx_buf[EUD_RX_MAX_FRAME];
        u8  rx_delivered;
        bool console_registered;
        void __iomem *ahb2phy_cfg;
        u32 original_ahb2phy_cfg;
};

static struct eud_port *eud;   /* one COM FIFO per board */

static inline struct eud_port *to_eud_port(struct uart_port *port)
{
        return container_of(port, struct eud_port, port);
}

/*
 * One register write is one FIFO entry.  udelay() is the only flow control that
 * works on this unit, so every write is paced.
 */
static inline void eud_put(void __iomem *base, unsigned int off, unsigned int v)
{
        udelay(EUD_TX_BYTE_US);
        writel_relaxed(v, base + off);
}

static void eud_send_frame(struct uart_port *port, const u8 *s, unsigned int n)
{
        void __iomem *base = port->membase;
        unsigned int i;

        eud_put(base, EUD_REG_COM_TX_ID, EUD_COM_UART_ID);
        eud_put(base, EUD_REG_COM_TX_LEN, n);
        for (i = 0; i < n; i++)
                eud_put(base, EUD_REG_COM_TX_DAT, s[i]);

        udelay(EUD_TX_FRAME_US);
}

/* tty write path: a workqueue, because the pacing sleeps between frames */
static void eud_tx_work(struct work_struct *work)
{
        struct eud_port *up = container_of(work, struct eud_port, tx_work);
        struct uart_port *port = &up->port;
        struct tty_port *tport;

        if (!port->state)
                return;
        tport = &port->state->port;

        for (;;) {
                unsigned long flags;
                u8 buf[EUD_TX_CHUNK];
                unsigned int n = 0;
                u8 ch;

                uart_port_lock_irqsave(port, &flags);
                if (uart_tx_stopped(port)) {
                        uart_port_unlock_irqrestore(port, flags);
                        break;
                }
                while (n < EUD_TX_CHUNK && kfifo_get(&tport->xmit_fifo, &ch)) {
                        buf[n++] = ch;
                        port->icount.tx++;
                }
                uart_port_unlock_irqrestore(port, flags);

                if (!n)
                        break;

                uart_port_lock_irqsave(port, &flags);
            eud_send_frame(port, buf, n);
            uart_port_unlock_irqrestore(port, flags);
        }

        if (kfifo_len(&tport->xmit_fifo) < WAKEUP_CHARS)
                uart_write_wakeup(port);
}

static unsigned int eud_tx_empty(struct uart_port *port)
{
        return TIOCSER_TEMT;
}

static void eud_start_tx(struct uart_port *port)
{
        struct eud_port *up = to_eud_port(port);

        schedule_work(&up->tx_work);
}

static void eud_stop_tx(struct uart_port *port)
{
}

static void eud_stop_rx(struct uart_port *port)
{
}

static void eud_set_mctrl(struct uart_port *port, unsigned int mctrl)
{
}

static unsigned int eud_get_mctrl(struct uart_port *port)
{
        return TIOCM_CTS | TIOCM_DSR | TIOCM_CAR;
}

static int eud_startup(struct uart_port *port)
{
        return 0;
}

static void eud_shutdown(struct uart_port *port)
{
        struct eud_port *up = to_eud_port(port);
        struct tty_port *tport;
        u8 ch;

        cancel_work_sync(&up->tx_work);

        if (!port->state)
                return;
        tport = &port->state->port;

        /*
         * Drain what the tty queued.  The pacing has to run in process
         * context, and a short lived writer (echo > /dev/ttyEUD0) closes the
         * port before the workqueue gets a chance to run - without this its
         * bytes are simply lost.
         */
        for (;;) {
                unsigned long flags;
                u8 buf[EUD_TX_CHUNK];
                unsigned int n = 0;

                uart_port_lock_irqsave(port, &flags);
                while (n < EUD_TX_CHUNK && kfifo_get(&tport->xmit_fifo, &ch)) {
                        buf[n++] = ch;
                        port->icount.tx++;
                }
                uart_port_unlock_irqrestore(port, flags);

                if (!n)
                        break;

                uart_port_lock_irqsave(port, &flags);
            eud_send_frame(port, buf, n);
            uart_port_unlock_irqrestore(port, flags);
        }
}

static void eud_set_termios(struct uart_port *port, struct ktermios *new,
                            const struct ktermios *old)
{
        /* the FIFO has no line control at all */
}

static const char *eud_type(struct uart_port *port)
{
        return "EUD";
}

static void eud_config_port(struct uart_port *port, int flags)
{
        if (flags & UART_CONFIG_TYPE)
                port->type = EUD_PORT_TYPE;
}

static int eud_verify_port(struct uart_port *port, struct serial_struct *ser)
{
        if (ser->type != PORT_UNKNOWN && ser->type != EUD_PORT_TYPE)
                return -EINVAL;
        return 0;
}

static const struct uart_ops eud_ops = {
        .tx_empty       = eud_tx_empty,
        .set_mctrl      = eud_set_mctrl,
        .get_mctrl      = eud_get_mctrl,
        .stop_tx        = eud_stop_tx,
        .start_tx       = eud_start_tx,
        .stop_rx        = eud_stop_rx,
        .startup        = eud_startup,
        .shutdown       = eud_shutdown,
        .set_termios    = eud_set_termios,
        .type           = eud_type,
        .config_port    = eud_config_port,
        .verify_port    = eud_verify_port,
};

static struct uart_driver eud_uart_driver = {
        .owner       = THIS_MODULE,
        .driver_name = "eud_com",
        .dev_name    = "ttyEUD",
        .major       = 0,
        .minor       = 0,
        .nr          = 1,
};

/*
 * Console.  Registered only when "console=eud" is on the command line (see the
 * file comment).  .device makes /dev/console bind to ttyEUD once the port is up.
 */
static void eud_console_write(struct console *co, const char *s,
                              unsigned int count)
{
        struct uart_port *port;
        unsigned long flags;

        if (!eud)
                return;
        port = &eud->port;

        uart_port_lock_irqsave(port, &flags);
        while (count) {
                unsigned int n = min_t(unsigned int, count, EUD_TX_CHUNK);

                eud_send_frame(port, (const u8 *)s, n);
                s += n;
                count -= n;
        }
        uart_port_unlock_irqrestore(port, flags);
}

static struct console eud_console = {
        .name   = "eud",
        .write  = eud_console_write,
        .device = uart_console_device,
        .flags  = CON_PRINTBUFFER,
        .index  = -1,
        .data   = &eud_uart_driver,
};

/*
 * Command channel.  Only the header is reliable, so the command travels in the
 * length byte: [0x81][cmd].  Payload bytes, when they do show up, are passed to
 * the tty instead.
 */
static void eud_command(struct eud_port *up, const u8 *data, unsigned int n)
{
        void __iomem *base = up->port.membase;
        unsigned int i;
        u8 cmd = n ? data[0] : 0;

        switch (cmd) {
        case 1:
                pr_info("eud: pong\n");
                break;
        case 2:
                pr_info("eud: regs");
                for (i = 0; i <= 0x60; i += 4)
                        pr_cont(" %02x=%08x", i, readl_relaxed(base + i));
                pr_cont("\n");
                break;
        case 3:
                pr_info("eud: polls=%u reports=%u last_status=%08x\n",
                        up->rx_polls, up->rx_reports, up->rx_last_status);
                break;
        default:
                pr_info("eud: unknown command %u\n", cmd);
                break;
        }
}

/* Length 2 reboots to bootloader. Disable EUD first so
 * the USB PHY goes back to the gadget/ABL, else the host never sees fastboot. */
static bool eud_reboot_pending;

static void eud_restore_ahb2phy(struct eud_port *up)
{
        writel(up->original_ahb2phy_cfg, up->ahb2phy_cfg);
        /* Complete restoration before handing the PHY back to ABL. */
        readl(up->ahb2phy_cfg);
}

static void eud_reboot_cmd(struct eud_port *up, unsigned int len)
{
	const char *what;
	if (eud_reboot_pending)
		return;
	if (len == 2)
		what = "bootloader";
	else
		return;
	eud_reboot_pending = true;
	pr_info("eud: reboot2 %s requested\n", what);
        eud_restore_ahb2phy(up);
	writel_relaxed(0, up->port.membase + EUD_REG_CSR_EUD_EN);
	wmb();
	kernel_restart((char *)what);
}

static void eud_rx_dispatch(struct eud_port *up)
{
        struct uart_port *port = &up->port;
        unsigned int i;
        unsigned long flags;

        up->rx_delivered = 0;
        if (up->rx_id == EUD_RX_UART_ID && up->rx_len == 2) {
                eud_reboot_cmd(up, up->rx_len);
        } else if ((up->rx_id == EUD_RX_CHAR_ID || up->rx_id == EUD_RX_CHAR_ID2 ||
             up->rx_id == EUD_RX_UART_ID) &&
            up->rx_have) {
                if (port->state) {
                        uart_port_lock_irqsave(port, &flags);
                        up->rx_delivered = tty_insert_flip_string(
                                &port->state->port, up->rx_buf, up->rx_have);
                        port->icount.rx += up->rx_delivered;
                        port->icount.buf_overrun += up->rx_have - up->rx_delivered;
                        up->rx_tty_bytes += up->rx_delivered;
                        uart_port_unlock_irqrestore(port, flags);
                        tty_flip_buffer_push(&port->state->port);
                } else {
                        uart_port_lock_irqsave(port, &flags);
                        up->rx_no_tty++;
                        uart_port_unlock_irqrestore(port, flags);
                }
        } else if (up->rx_id == EUD_RX_CMD_ID) {
                eud_command(up, up->rx_buf, up->rx_have);
        } else if (up->rx_reports < EUD_RX_REPORTS) {
                pr_info("eud: rx id=%02x len=%02x data", up->rx_id, up->rx_have);
                for (i = 0; i < up->rx_have; i++)
                        pr_cont(" %02x", up->rx_buf[i]);
                pr_cont("\n");
                up->rx_reports++;
        }
}

/*
 * The verified AHB2PHY one-wait setting enables consecutive FIFO reads.
 * Collect the complete frame under the shared TX lock before any logging.
 * Linux ABC/DEFG were verified before enabling multi-byte tty delivery.
 */
static void eud_rx_work(struct work_struct *work)
{
        struct eud_port *up = container_of(to_delayed_work(work),
                                           struct eud_port, rx_work);
        void __iomem *base = up->port.membase;
        u32 id, len, s1, s2;
        unsigned int i;
        unsigned long flags;

        uart_port_lock_irqsave(&up->port, &flags);
        up->rx_polls++;
        s1 = readl(base + EUD_REG_INT_STATUS_1);
        up->rx_last_status = s1;
        if (!(s1 & EUD_INT_RX_PENDING))
                goto unlock;

        up->rx_pending++;
        id = readl(base + EUD_REG_COM_RX_ID) & 0xff;
        len = readl(base + EUD_REG_COM_RX_LEN) & 0xff;
        up->rx_last_id = id;
        up->rx_last_len = len;
        if (id == EUD_RX_UART_ID && len == 2) {
                up->rx_f1++;
                uart_port_unlock_irqrestore(&up->port, flags);
                eud_reboot_cmd(up, len);
                goto out;
        }
        if ((id != EUD_RX_UART_ID && id != EUD_RX_CHAR_ID &&
             id != EUD_RX_CHAR_ID2 && id != EUD_RX_CMD_ID) ||
            len < 1 || len > EUD_RX_MAX_FRAME) {
                up->rx_bad_headers++;
                up->rx_bad_id = id;
                up->rx_bad_len = len;
                goto unlock;
        }

        up->rx_id = id;
        up->rx_len = len;
        up->rx_have = len;
        for (i = 0; i < len; i++)
                up->rx_buf[i] = readl(base + EUD_REG_COM_RX_DAT) & 0xff;
        s2 = readl(base + EUD_REG_INT_STATUS_1);
        up->rx_frames++;
        up->rx_bytes += len;
        up->rx_last_after = s2;
        uart_port_unlock_irqrestore(&up->port, flags);

        /* Finish the receipt before tty echo/command output can be queued. */
        if (len == 1) {
                if (up->rx_buf[0] == 0x15)
                        pr_info("eud: tty byte=15 polls=%u pending=%u bad=%u frames=%u bytes=%u tty_before=%u no_tty=%u overrun=%u bad_id=%02x bad_len=%u\n",
                                up->rx_polls, up->rx_pending, up->rx_bad_headers,
                                up->rx_frames, up->rx_bytes, up->rx_tty_bytes,
                                up->rx_no_tty, up->port.icount.buf_overrun,
                                up->rx_bad_id, up->rx_bad_len);
                else
                        pr_info("eud: tty byte=%02x\n", up->rx_buf[0]);
        } else {
                pr_info("eud: rx frame len=%u data=%*ph s1_after=%08x\n",
                        len, len, up->rx_buf, s2);
        }
        eud_rx_dispatch(up);
        if (id == EUD_RX_UART_ID && up->rx_delivered != len)
                pr_warn("eud: tty accepted %u/%u bytes\n", up->rx_delivered, len);
        goto out;

unlock:
        uart_port_unlock_irqrestore(&up->port, flags);
out:
        schedule_delayed_work(&up->rx_work, msecs_to_jiffies(EUD_RX_POLL_MS));
}

/* Read a coherent software snapshot, never touch the hardware for diagnostics.
 * The counter updates reuse the existing RX/TX lock and MMIO reads. There is
 * no extra FIFO access, polling, interrupt setup or status write. Ctrl-U also
 * includes counters in its existing receipt (before delivery of that byte),
 * so observing a failed native input does not require a long shell command.
 */
static ssize_t rx_stats_show(struct device *dev, struct device_attribute *attr,
                             char *buf)
{
        struct uart_port *port = dev_get_drvdata(dev);
        struct eud_port *up = to_eud_port(port);
        unsigned long flags;
        ssize_t n;

        uart_port_lock_irqsave(port, &flags);
        n = sysfs_emit(buf,
                "polls=%u pending=%u bad=%u frames=%u f1=%u bytes=%u tty=%u no_tty=%u overrun=%u status=%08x id=%02x len=%u after=%08x bad_id=%02x bad_len=%u\n",
                up->rx_polls, up->rx_pending, up->rx_bad_headers,
                up->rx_frames, up->rx_f1, up->rx_bytes, up->rx_tty_bytes,
                up->rx_no_tty, port->icount.buf_overrun, up->rx_last_status,
                up->rx_last_id, up->rx_last_len, up->rx_last_after,
                up->rx_bad_id, up->rx_bad_len);
        uart_port_unlock_irqrestore(port, flags);
        return n;
}
static DEVICE_ATTR_RO(rx_stats);

static struct attribute *eud_attrs[] = {
        &dev_attr_rx_stats.attr,
        NULL,
};
ATTRIBUTE_GROUPS(eud);

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

static void eud_remove(struct platform_device *pdev)
{
        struct uart_port *port = platform_get_drvdata(pdev);
        struct eud_port *up = to_eud_port(port);

        cancel_delayed_work_sync(&up->rx_work);
        cancel_work_sync(&up->tx_work);
        if (up->console_registered)
                unregister_console(&eud_console);
        uart_remove_one_port(&eud_uart_driver, port);
        eud_restore_ahb2phy(up);
        eud = NULL;
}

static const struct of_device_id eud_com_dt_match[] = {
        { .compatible = "qcom,sm8150-eud-com" },
        { }
};
MODULE_DEVICE_TABLE(of, eud_com_dt_match);

static struct platform_driver eud_com_driver = {
        .probe  = eud_probe,
        .remove = eud_remove,
        .driver = {
                .name           = "qcom_eud_com",
                .of_match_table = eud_com_dt_match,
                .dev_groups     = eud_groups,
        },
};

static int __init eud_init(void)
{
        int ret;

        ret = uart_register_driver(&eud_uart_driver);
        if (ret)
                return ret;

        ret = platform_driver_register(&eud_com_driver);
        if (ret)
                uart_unregister_driver(&eud_uart_driver);

        return ret;
}
module_init(eud_init);

static void __exit eud_exit(void)
{
        platform_driver_unregister(&eud_com_driver);
        uart_unregister_driver(&eud_uart_driver);
}
module_exit(eud_exit);

MODULE_DESCRIPTION("Qualcomm EUD COM console, tty and command channel");
MODULE_LICENSE("GPL");
