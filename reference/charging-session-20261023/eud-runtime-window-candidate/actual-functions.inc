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

struct eud_port {
        struct uart_port port;
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
	if (up->tx_stopping)
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

        if (!port->state)
                return;
        tport = &port->state->port;
	mutex_lock(&up->tx_mutex);

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
                while (n < EUD_TX_CHUNK && kfifo_get(&tport->xmit_fifo, &ch)) {
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

        if (!up->rx_irq_started || up->rx_stopping || up->rx_bootloader_pending)
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
        if (kick && !READ_ONCE(eud->rx_stopping))
                mod_delayed_work(system_percpu_wq, &eud->rx_work, 0);
}
