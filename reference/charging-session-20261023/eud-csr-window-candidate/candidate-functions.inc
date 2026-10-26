#define EUD_REG_COM_TX_ID      0x0000

#define EUD_REG_COM_TX_LEN     0x0004

#define EUD_REG_COM_TX_DAT     0x0008

#define EUD_REG_COM_RX_ID      0x000C

#define EUD_REG_COM_RX_LEN     0x0010

#define EUD_REG_COM_RX_DAT     0x0014

#define EUD_REG_INT1_EN_MASK   0x0024

#define EUD_REG_INT_STATUS_1   0x0044

#define EUD_REG_CSR_EUD_EN     0x1014

#define EUD_AHB2PHY_ONE_WAIT   0x11

#define EUD_COM_UART_ID        0x90    /* the id this port transmits with */

#define EUD_TX_CHUNK           4u      /* data bytes per frame: six entries */

#define EUD_TX_BYTE_US         200

#define EUD_TX_FRAME_US        2000

#define EUD_TX_JOURNAL_DEPTH   512

#define EUD_TX_SOURCE_TTY      1

#define EUD_TX_SOURCE_CONSOLE  2

#define EUD_RX_MAX_FRAME       14    /* MAX_FIFO_SIZE in kernel/msm */

#define EUD_RX_UART_ID         0x90    /* upstream UART_ID: the channel */

#define EUD_RX_CMD_ID          0x81    /* APPS exec-env: our command channel */

#define EUD_RX_CHAR_ID         0x82    /* payload is tty input */

#define EUD_RX_CHAR_ID2        0x83    /* alternate id for the next char */

#define EUD_INT_RX_PENDING     BIT(0)  /* INT_STATUS_1: RX data available */

#define EUD_RX_QUEUE_DEPTH     32

#define EUD_IRQ_FAULT_QUEUE    3

#define EUD_IRQ_FAULT_HEADER   2

#define EUD_RX_POLL_MS         20

#define EUD_INT_RX             BIT(0)  /* INT_STATUS_1: RX data pending */

#define EUD_RX_IRQ_EMPTY_MAX   8

#define EUD_RX_IRQ_GRACE_MS    100     /* five status periods without progress */

#define EUD_IRQ_FAULT_EMPTY    1

#define EUD_IRQ_FAULT_WATCHDOG 4

#define EUD_IRQ_FAULT_MASK     5

enum eud_com_window_state {
        EUD_COM_ACTIVE,
        EUD_COM_QUIETING,
        EUD_COM_QUIET,
        EUD_COM_CANCELLED,
        EUD_COM_REMOVED,
};

struct eud_com_window_result {
        u64 cookie;
        enum eud_com_window_state state;
        bool software_quiet;
        bool cancelled;
        bool restored;
        bool csr_touched;
        bool hardware_owned;
        bool ahb2phy_touched;
        int error;
        int restore_error;
};

struct eud_com_csr_result {
        u64 cookie;
        bool software_quiet;
        bool cancelled;
        bool hardware_owned;
        bool saved_valid;
        bool readback_valid;
        bool disabled_verified;
        bool restored;
        bool removed;
        bool csr_touched;
        u32 saved_value;
        u32 readback;
        int error;
        int enter_error;
        int restore_error;
};


struct eud_tx_record {
        u8 len;
        u8 source;
        u8 data[EUD_TX_CHUNK];
};

struct eud_rx_frame {
        u32 after;
        u8 id;
        u8 len;
        u8 data[EUD_RX_MAX_FRAME];
        u8 source;
};

enum eud_rx_source {
        EUD_RX_SOURCE_POLL,
        EUD_RX_SOURCE_IRQ,
        EUD_RX_SOURCE_CONSOLE,
};

struct eud_rx_snapshot {
        u32 polls, pending, bad, frames, bytes, tty_before, no_tty, overrun;
        u32 bad_id, bad_len, irqs, irq_frames, poll_frames, empty;
        u32 watchdog, drops, fault, active;
};

struct eud_port {
        struct uart_port port;
        bool window_quiet;
        bool window_irq_enabled;
        bool window_system_pm;
        bool window_runtime_pm;
        enum eud_com_window_state window_state;
        u64 window_cookie;
        struct eud_com_csr_result window_csr;
        struct work_struct tx_work;
	struct mutex tx_mutex;
	bool tx_stopping;
        struct delayed_work rx_work;
        u64 tx_journal_total;
        u32 tx_journal_head;
        u32 tx_journal_count;
        struct eud_tx_record tx_journal[EUD_TX_JOURNAL_DEPTH];
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
        int rx_irq;
        bool rx_irq_requested;
        bool rx_irq_mapping_owned;
        bool rx_irq_enabled;
        bool rx_irq_started;
        bool rx_stopping;
        bool rx_bootloader_pending;
        u8 rx_bootloader_source;
        bool rx_mask_changed;
        bool rx_fault_reported;
        u32 original_int1_mask;
        u32 rx_irq_events;
        u32 rx_irq_frames;
        u32 rx_poll_frames;
        u32 rx_console_frames;
        u32 rx_console_checks;
        u32 rx_console_f1;
        u32 rx_console_empty_irqs;
        bool rx_console_irq_credit;
        u32 rx_irq_empty;
        u32 rx_irq_empty_streak;
        u32 rx_watchdog_misses;
        bool rx_irq_waiting;
        unsigned long rx_irq_wait_start;
        u32 rx_irq_waits;
        u32 rx_irq_recovered;
        u32 rx_irq_wait_cleared;
        u32 rx_irq_wait_peak_ms;
        u8 rx_gic_first;
        u8 rx_gic_last;
        int rx_gic_error;
        u32 rx_queue_drops;
        u32 rx_irq_fault;
        u32 rx_queue_head;
        u32 rx_queue_tail;
        u32 rx_queue_count;
        struct eud_rx_frame rx_queue[EUD_RX_QUEUE_DEPTH];
};

static struct eud_port *eud;
static bool eud_reboot_pending;

static inline struct eud_port *to_eud_port(struct uart_port *port)
{
        return container_of(port, struct eud_port, port);
}

static inline void eud_put(void __iomem *base, unsigned int off, unsigned int v)
{
        udelay(EUD_TX_BYTE_US);
        writel_relaxed(v, base + off);
}

static void eud_send_frame(struct uart_port *port, const u8 *s, unsigned int n,
                            u8 source)
{
        struct eud_port *up = to_eud_port(port);
        struct eud_tx_record *record;
        void __iomem *base = port->membase;
        unsigned int i;

	/* The reboot handoff sets this under the UART lock. */
	if (up->tx_stopping || up->window_quiet)
		return;

        eud_put(base, EUD_REG_COM_TX_ID, EUD_COM_UART_ID);
        eud_put(base, EUD_REG_COM_TX_LEN, n);
        for (i = 0; i < n; i++)
                eud_put(base, EUD_REG_COM_TX_DAT, s[i]);

        udelay(EUD_TX_FRAME_US);

        /* Software evidence of the issued MMIO values, not a device ACK.
         * Both writers hold the UART lock; do not print or change pacing.
         */
        record = &up->tx_journal[up->tx_journal_head];
        memset(record, 0, sizeof(*record));
        record->len = n;
        record->source = source;
        memcpy(record->data, s, n);
        up->tx_journal_head = (up->tx_journal_head + 1) % EUD_TX_JOURNAL_DEPTH;
        up->tx_journal_count = min_t(u32, up->tx_journal_count + 1,
                                    EUD_TX_JOURNAL_DEPTH);
        up->tx_journal_total++;
}

static void eud_tx_work(struct work_struct *work)
{
        struct eud_port *up = container_of(work, struct eud_port, tx_work);
        struct uart_port *port = &up->port;
        struct tty_port *tport;

        if (READ_ONCE(up->window_quiet) || !port->state)
                return;
        tport = &port->state->port;
	mutex_lock(&up->tx_mutex);

        for (;;) {
                unsigned long flags;
                u8 buf[EUD_TX_CHUNK];
                unsigned int n = 0;
                u8 ch;

                uart_port_lock_irqsave(port, &flags);
                if (uart_tx_stopped(port) || up->window_quiet) {
                        uart_port_unlock_irqrestore(port, flags);
                        break;
                }
                while (!up->window_quiet && n < EUD_TX_CHUNK &&
                       kfifo_get(&tport->xmit_fifo, &ch)) {
                        buf[n++] = ch;
                        port->icount.tx++;
                }
                uart_port_unlock_irqrestore(port, flags);

                if (!n)
                        break;

                uart_port_lock_irqsave(port, &flags);
            eud_send_frame(port, buf, n, EUD_TX_SOURCE_TTY);
            uart_port_unlock_irqrestore(port, flags);
        }

	mutex_unlock(&up->tx_mutex);

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

        if (!READ_ONCE(up->window_quiet))
                schedule_work(&up->tx_work);
}

static void eud_stop_tx(struct uart_port *port)
{
}

static void eud_stop_rx(struct uart_port *port)
{
}

static int eud_startup(struct uart_port *port)
{
        return READ_ONCE(to_eud_port(port)->window_quiet) ? -EBUSY : 0;
}

static void eud_shutdown(struct uart_port *port)
{
        struct eud_port *up = to_eud_port(port);
        struct tty_port *tport;
        u8 ch;

        cancel_work_sync(&up->tx_work);

        if (READ_ONCE(up->window_quiet) || !port->state)
                return;
        tport = &port->state->port;
	mutex_lock(&up->tx_mutex);

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
                while (!up->window_quiet && n < EUD_TX_CHUNK &&
                       kfifo_get(&tport->xmit_fifo, &ch)) {
                        buf[n++] = ch;
                        port->icount.tx++;
                }
                uart_port_unlock_irqrestore(port, flags);

                if (!n)
                        break;

                uart_port_lock_irqsave(port, &flags);
            eud_send_frame(port, buf, n, EUD_TX_SOURCE_TTY);
            uart_port_unlock_irqrestore(port, flags);
        }
	mutex_unlock(&up->tx_mutex);
}

static void eud_restore_ahb2phy(struct eud_port *up)
{
        writel(up->original_ahb2phy_cfg, up->ahb2phy_cfg);
        /* Complete restoration before handing the PHY back to ABL. */
        readl(up->ahb2phy_cfg);
}

static void eud_rx_irq_stop_locked(struct eud_port *up, u32 fault)
{
        up->rx_irq_waiting = false;
        up->rx_console_irq_credit = false;
        if (up->rx_irq_enabled) {
                up->rx_irq_enabled = false;
                disable_irq_nosync(up->rx_irq);
        }
        if (up->rx_mask_changed) {
                writel(up->original_int1_mask,
                       up->port.membase + EUD_REG_INT1_EN_MASK);
                readl(up->port.membase + EUD_REG_INT1_EN_MASK);
                up->rx_mask_changed = false;
        }
        if (fault && !up->rx_irq_fault)
                up->rx_irq_fault = fault;
}

static void eud_reboot_cmd(struct eud_port *up, unsigned int len)
{
	unsigned long flags;
	const char *what;

	if (len != 2)
		return;
	what = "bootloader";
	uart_port_lock_irqsave(&up->port, &flags);
	if (eud_reboot_pending || up->window_quiet) {
		uart_port_unlock_irqrestore(&up->port, flags);
		return;
	}
	eud_reboot_pending = true;
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

static int eud_rx_collect_locked(struct eud_port *up, u32 s1, u8 source)
{
        void __iomem *base = up->port.membase;
        struct eud_rx_frame frame = {};
        u32 id, len;
        unsigned int i;

        up->rx_last_status = s1;
        if (!(s1 & EUD_INT_RX_PENDING))
                return 0;

        up->rx_pending++;
        id = readl(base + EUD_REG_COM_RX_ID) & 0xff;
        len = readl(base + EUD_REG_COM_RX_LEN) & 0xff;
        up->rx_last_id = id;
        up->rx_last_len = len;
        if (id == EUD_RX_UART_ID && len == 2) {
                up->rx_f1++;
                up->rx_bootloader_pending = true;
                up->rx_bootloader_source = source;
                if (source == EUD_RX_SOURCE_CONSOLE)
                        up->rx_console_f1++;
                eud_rx_irq_stop_locked(up, 0);
                return 2;
        }
        if ((id != EUD_RX_UART_ID && id != EUD_RX_CHAR_ID &&
             id != EUD_RX_CHAR_ID2 && id != EUD_RX_CMD_ID) ||
            len < 1 || len > EUD_RX_MAX_FRAME) {
                up->rx_bad_headers++;
                up->rx_bad_id = id;
                up->rx_bad_len = len;
                return -EINVAL;
        }

        frame.id = id;
        frame.len = len;
        frame.source = source;
        for (i = 0; i < len; i++)
                frame.data[i] = readl(base + EUD_REG_COM_RX_DAT) & 0xff;
        frame.after = readl(base + EUD_REG_INT_STATUS_1);
        up->rx_frames++;
        up->rx_bytes += len;
        up->rx_last_after = frame.after;
        if (source == EUD_RX_SOURCE_IRQ)
                up->rx_irq_frames++;
        else if (source == EUD_RX_SOURCE_CONSOLE)
                up->rx_console_frames++;
        else
                up->rx_poll_frames++;
        if (up->rx_queue_count == EUD_RX_QUEUE_DEPTH) {
                up->rx_queue_drops++;
                return -ENOSPC;
        }
        up->rx_queue[up->rx_queue_head] = frame;
        up->rx_queue_head = (up->rx_queue_head + 1) % EUD_RX_QUEUE_DEPTH;
        up->rx_queue_count++;
        return 1;
}

static int eud_console_rx_locked(struct eud_port *up)
{
        u32 s1;
        int ret;

        if (!up->rx_irq_started || up->rx_stopping || up->window_quiet ||
            up->rx_bootloader_pending)
                return 0;
        up->rx_console_checks++;
        s1 = readl(up->port.membase + EUD_REG_INT_STATUS_1);
        ret = eud_rx_collect_locked(up, s1, EUD_RX_SOURCE_CONSOLE);
        if (ret > 0) {
                /* The level may already have reached the GIC before DAT was
                 * consumed. Credit at most ONE subsequent empty IRQ, not an
                 * unlimited storm. Any IRQ observation consumes this credit.
                 */
                if (up->rx_irq_enabled)
                        up->rx_console_irq_credit = true;
                up->rx_irq_empty_streak = 0;
                if (up->rx_irq_waiting) {
                        up->rx_irq_wait_peak_ms = max_t(u32,
                                up->rx_irq_wait_peak_ms,
                                jiffies_to_msecs(jiffies - up->rx_irq_wait_start));
                        up->rx_irq_wait_cleared++;
                        up->rx_irq_waiting = false;
                }
        } else if (ret < 0) {
                eud_rx_irq_stop_locked(up,
                        ret == -ENOSPC ? EUD_IRQ_FAULT_QUEUE : EUD_IRQ_FAULT_HEADER);
        }
        return ret;
}

static void eud_console_write_legacy(struct console *co, const char *s,
                              unsigned int count)
{
        struct uart_port *port;
        unsigned long flags;
        bool kick, collect;
        int ret;

        if (!eud)
                return;
        port = &eud->port;

        uart_port_lock_irqsave(port, &flags);
        /* Legacy printk also disables IRQs outside this callback. Service
         * RX at whole TX frame boundaries rather than waiting for the entire
         * record. The shared collector finishes DAT before any further TX;
         * receipt/tty/F1 stay in work context after releasing this lock.
         */
        ret = eud_console_rx_locked(eud);
        kick = ret != 0;
        collect = ret >= 0;
        while (count) {
                unsigned int n = min_t(unsigned int, count, EUD_TX_CHUNK);

                eud_send_frame(port, (const u8 *)s, n, EUD_TX_SOURCE_CONSOLE);
                s += n;
                count -= n;
                if (collect) {
                        ret = eud_console_rx_locked(eud);
                        kick |= ret != 0;
                        collect = ret >= 0;
                }
        }
        uart_port_unlock_irqrestore(port, flags);
        if (kick && !READ_ONCE(eud->rx_stopping) &&
            !READ_ONCE(eud->window_quiet))
                mod_delayed_work(system_percpu_wq, &eud->rx_work, 0);
}

static irqreturn_t eud_rx_irq(int irq, void *data)
{
        struct eud_port *up = data;
        unsigned long flags;
        bool kick = false;
        bool console_credit;
        u32 s1;
        int ret;

        uart_port_lock_irqsave(&up->port, &flags);
        up->rx_irq_events++;
        console_credit = up->rx_console_irq_credit;
        up->rx_console_irq_credit = false;
        if (!up->rx_stopping && !up->window_quiet && up->rx_irq_enabled) {
                s1 = readl(up->port.membase + EUD_REG_INT_STATUS_1);
                ret = eud_rx_collect_locked(up, s1, EUD_RX_SOURCE_IRQ);
                if (!ret) {
                        up->rx_irq_empty++;
                        if (console_credit) {
                                up->rx_console_empty_irqs++;
                        } else if (++up->rx_irq_empty_streak >= EUD_RX_IRQ_EMPTY_MAX) {
                                eud_rx_irq_stop_locked(up, EUD_IRQ_FAULT_EMPTY);
                                kick = true;
                        }
                } else {
                        if (ret > 0 && up->rx_irq_waiting) {
                                up->rx_irq_wait_peak_ms = max_t(u32,
                                        up->rx_irq_wait_peak_ms,
                                        jiffies_to_msecs(jiffies - up->rx_irq_wait_start));
                                up->rx_irq_recovered++;
                                up->rx_irq_waiting = false;
                        }
                        up->rx_irq_empty_streak = 0;
                        kick = true;
                        if (ret < 0)
                                eud_rx_irq_stop_locked(up,
                                        ret == -ENOSPC ? EUD_IRQ_FAULT_QUEUE :
                                                        EUD_IRQ_FAULT_HEADER);
                }
        }
        uart_port_unlock_irqrestore(&up->port, flags);
        if (kick && !READ_ONCE(up->rx_stopping) &&
            !READ_ONCE(up->window_quiet))
                mod_delayed_work(system_percpu_wq, &up->rx_work, 0);
        return IRQ_HANDLED;
}

static void eud_rx_snapshot_locked(struct eud_port *up,
                                   struct eud_rx_snapshot *s)
{
        s->polls = up->rx_polls;
        s->pending = up->rx_pending;
        s->bad = up->rx_bad_headers;
        s->frames = up->rx_frames;
        s->bytes = up->rx_bytes;
        s->tty_before = up->rx_tty_bytes;
        s->no_tty = up->rx_no_tty;
        s->overrun = up->port.icount.buf_overrun;
        s->bad_id = up->rx_bad_id;
        s->bad_len = up->rx_bad_len;
        s->irqs = up->rx_irq_events;
        s->irq_frames = up->rx_irq_frames;
        s->poll_frames = up->rx_poll_frames;
        s->empty = up->rx_irq_empty;
        s->watchdog = up->rx_watchdog_misses;
        s->drops = up->rx_queue_drops;
        s->fault = up->rx_irq_fault;
        s->active = up->rx_irq_enabled;
}

static void eud_rx_work(struct work_struct *work)
{
        struct eud_port *up = container_of(to_delayed_work(work),
                                           struct eud_port, rx_work);
        struct eud_rx_frame frame;
        struct eud_rx_snapshot stats;
        unsigned long flags;
        bool arm_notice = false, fault_notice = false;
        bool have = false, f1, queued;
        u8 f1_source;
        u32 s1;

        uart_port_lock_irqsave(&up->port, &flags);
        if (up->rx_stopping || up->window_quiet) {
                uart_port_unlock_irqrestore(&up->port, flags);
                return;
        }
        if (!up->rx_irq_started) {
                up->rx_irq_started = true;
                if (up->rx_irq_requested) {
                        up->original_int1_mask = readl(up->port.membase +
                                                      EUD_REG_INT1_EN_MASK) & 0xff;
                        up->rx_mask_changed = true;
                        /* Only RX may assert this handler. Do not enable
                         * stuck TX/VBUS/charger levels during this diagnostic.
                         */
                        writel((u32)EUD_INT_RX,
                               up->port.membase + EUD_REG_INT1_EN_MASK);
                        if ((readl(up->port.membase + EUD_REG_INT1_EN_MASK) & 0xff) !=
                            EUD_INT_RX) {
                                eud_rx_irq_stop_locked(up, EUD_IRQ_FAULT_MASK);
                        } else {
                                up->rx_irq_enabled = true;
                                /* Direct SM8150 GICv3 IRQ: no sleeping bus_lock.
                                 * The UART lock prevents remove/start races.
                                 */
                                enable_irq(up->rx_irq);
                        }
                        arm_notice = true;
                }
        }
        /* A pending status can race an IRQ waiting for the UART lock. Give
         * the IRQ unlocked execution opportunities before declaring failure.
         * Keep the original 20 ms observations; only persistently unserviced
         * data reaches the bounded watchdog. Never collect DAT while the IRQ
         * is enabled, or count fallback data as IRQ success.
         */
        if (!up->rx_queue_count && !up->rx_bootloader_pending) {
                up->rx_polls++;
                s1 = readl(up->port.membase + EUD_REG_INT_STATUS_1);
                if ((s1 & EUD_INT_RX_PENDING) && up->rx_irq_enabled) {
                        if (!up->rx_irq_waiting) {
                                up->rx_irq_waiting = true;
                                up->rx_irq_wait_start = jiffies;
                                up->rx_irq_waits++;
                                up->rx_gic_first = eud_rx_gic_snapshot_locked(up);
                        } else if (time_after_eq(jiffies,
                                   up->rx_irq_wait_start +
                                   msecs_to_jiffies(EUD_RX_IRQ_GRACE_MS))) {
                                up->rx_gic_last = eud_rx_gic_snapshot_locked(up);
                                up->rx_irq_wait_peak_ms = max_t(u32,
                                        up->rx_irq_wait_peak_ms,
                                        jiffies_to_msecs(jiffies - up->rx_irq_wait_start));
                                up->rx_watchdog_misses++;
                                eud_rx_irq_stop_locked(up, EUD_IRQ_FAULT_WATCHDOG);
                        }
                } else if (up->rx_irq_waiting) {
                        up->rx_irq_wait_cleared++;
                        up->rx_irq_waiting = false;
                }
                if (!up->rx_irq_enabled)
                        eud_rx_collect_locked(up, s1, EUD_RX_SOURCE_POLL);
        }
        f1 = up->rx_bootloader_pending;
        f1_source = up->rx_bootloader_source;
        if (!f1 && up->rx_queue_count) {
                frame = up->rx_queue[up->rx_queue_tail];
                up->rx_queue_tail = (up->rx_queue_tail + 1) % EUD_RX_QUEUE_DEPTH;
                up->rx_queue_count--;
                /* Only this work item owns the existing dispatch buffer. */
                up->rx_id = frame.id;
                up->rx_len = frame.len;
                up->rx_have = frame.len;
                memcpy(up->rx_buf, frame.data, frame.len);
                have = true;
        }
        queued = up->rx_queue_count != 0;
        eud_rx_snapshot_locked(up, &stats);
        if (up->rx_irq_fault && !up->rx_fault_reported) {
                up->rx_fault_reported = true;
                fault_notice = true;
        }
        uart_port_unlock_irqrestore(&up->port, flags);

        if (arm_notice)
                pr_info("eud: RX46 IRQ armed virq=%d active=%u mask=01 original=%02x grace_ms=%u\n",
                        up->rx_irq, stats.active, up->original_int1_mask,
                        EUD_RX_IRQ_GRACE_MS);
        if (fault_notice)
                pr_warn("eud: RX46 IRQ fallback fault=%u irqs=%u irq_frames=%u watchdog=%u empty=%u drops=%u\n",
                        stats.fault, stats.irqs, stats.irq_frames,
                        stats.watchdog, stats.empty, stats.drops);
        if (f1) {
                pr_info("eud: RX46 F1 via=%s irqs=%u fault=%u\n",
                        eud_rx_source_name(f1_source), stats.irqs, stats.fault);
                eud_reboot_cmd(up, 2);
                return;
        }
        if (!have)
                goto out;
        /* Finish the receipt before tty echo/command output can be queued. */
        if (frame.len == 1) {
                if (up->rx_buf[0] == 0x15)
                        pr_info("eud: tty byte=15 polls=%u pending=%u bad=%u frames=%u bytes=%u tty_before=%u no_tty=%u overrun=%u bad_id=%02x bad_len=%u irqs=%u irq_frames=%u poll_frames=%u empty=%u watchdog=%u drops=%u fault=%u active=%u\n",
                                stats.polls, stats.pending, stats.bad, stats.frames,
                                stats.bytes, stats.tty_before, stats.no_tty,
                                stats.overrun, stats.bad_id, stats.bad_len,
                                stats.irqs, stats.irq_frames, stats.poll_frames,
                                stats.empty, stats.watchdog, stats.drops,
                                stats.fault, stats.active);
                else
                        pr_info("eud: tty byte=%02x\n", up->rx_buf[0]);
        } else {
                pr_info("eud: rx frame len=%u data=%*ph s1_after=%08x via=%s\n",
                        frame.len, frame.len, up->rx_buf, frame.after,
                        eud_rx_source_name(frame.source));
        }
        eud_rx_dispatch(up);
        if (frame.id == EUD_RX_UART_ID && up->rx_delivered != frame.len)
                pr_warn("eud: tty accepted %u/%u bytes\n", up->rx_delivered, frame.len);
out:
        if (!READ_ONCE(up->rx_stopping) && !READ_ONCE(up->window_quiet))
                schedule_delayed_work(&up->rx_work,
                                      queued ? 0 : msecs_to_jiffies(EUD_RX_POLL_MS));
}

/* Internal COM software window. eud_window_lock also serializes pointer
 * lifetime with probe/remove and both PM paths. No inter-driver calls here.
 */
static DEFINE_MUTEX(eud_window_lock);
static u64 eud_window_sequence;
static u64 eud_window_orphan;
static struct eud_com_csr_result eud_csr_orphan;

static void eud_window_result(struct eud_port *up,
                              struct eud_com_window_result *result, int error)
{
        *result = (struct eud_com_window_result) {
                .cookie = up ? up->window_cookie : 0,
                .state = up ? up->window_state : EUD_COM_REMOVED,
                .software_quiet = up && up->window_quiet,
                .csr_touched = up && up->window_csr.csr_touched,
                .hardware_owned = up && up->window_csr.hardware_owned,
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
        up->window_csr = (struct eud_com_csr_result) {
                .cookie = up->window_cookie,
        };
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
                if (cancelled) {
                        eud_window_orphan = 0;
                        /* Acknowledgment releases reprobe only, never repairs
                         * removed MMIO or converts its receipt to restored.
                         */
                        eud_csr_orphan = (struct eud_com_csr_result) { 0 };
                }
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
        else if (up->window_csr.hardware_owned)
                ret = -EBUSY;
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

static void eud_remove_locked(struct platform_device *pdev)
{
        struct uart_port *port = platform_get_drvdata(pdev);
        struct eud_port *up = to_eud_port(port);
        unsigned long flags;
        bool borrowed = up->window_quiet;

        uart_port_lock_irqsave(port, &flags);
        if (borrowed) {
                eud_window_orphan = up->window_cookie;
                up->window_state = EUD_COM_REMOVED;
                /* Keep a terminal receipt independently from software orphan
                 * acknowledgment. No access to removed CSR can restore it.
                 */
                eud_csr_orphan = up->window_csr;
                eud_csr_orphan.removed = true;
                eud_csr_orphan.restored = false;
                eud_csr_orphan.software_quiet = true;
                eud_csr_orphan.cancelled = true;
                up->tx_stopping = true;
        }
        up->rx_stopping = true;
        eud_rx_irq_stop_locked(up, 0);
        uart_port_unlock_irqrestore(port, flags);
        if (up->rx_irq_requested) {
                free_irq(up->rx_irq, up);
                up->rx_irq_requested = false;
        }
        cancel_delayed_work_sync(&up->rx_work);
        cancel_work_sync(&up->tx_work);
        if (up->console_registered)
                unregister_console(&eud_console);
        uart_remove_one_port(&eud_uart_driver, port);
        /* unregister_console and UART removal have now joined every producer.
         * A callback that passed its gate before stopping may have queued RX
         * or TX after the early cancellations. Join both one final time before
         * mappings/global state can be released, for borrowed and normal exit.
         */
        cancel_delayed_work_sync(&up->rx_work);
        cancel_work_sync(&up->tx_work);
        /* A live software borrower never changed AHB2PHY. Do not impose
         * probe history on its external controller/PHY session during unbind.
         * The endpoint is terminal; end(old_cookie) returns ENODEV and
         * acknowledges cancellation before a later probe may touch hardware.
         */
        if (!borrowed)
                eud_restore_ahb2phy(up);
        if (up->rx_irq_mapping_owned)
                irq_dispose_mapping(up->rx_irq);
        eud = NULL;
}

static void eud_remove(struct platform_device *pdev)
{
        mutex_lock(&eud_window_lock);
        eud_remove_locked(pdev);
        platform_set_drvdata(pdev, NULL);
        mutex_unlock(&eud_window_lock);
}
