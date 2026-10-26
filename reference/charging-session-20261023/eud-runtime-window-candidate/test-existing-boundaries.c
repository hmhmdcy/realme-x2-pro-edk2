/* Actual unchanged driver functions with fake OS/MMIO, never a kernel module. */
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>

typedef uint8_t u8;
typedef uint32_t u32;
typedef uint64_t u64;
#define __iomem
#define BIT(n) (1u << (n))
#define READ_ONCE(v) (v)
#define container_of(p, type, member) ((type *)((char *)(p) - offsetof(type, member)))
#define min_t(type, a, b) ((type)(a) < (type)(b) ? (type)(a) : (type)(b))
#define max_t(type, a, b) ((type)(a) > (type)(b) ? (type)(a) : (type)(b))
#define WAKEUP_CHARS 256
#define TIOCSER_TEMT 1
#define uart_port_lock_irqsave(p, f) do { *(f) = 0; } while (0)
#define uart_port_unlock_irqrestore(p, f) do {} while (0)
struct work_struct { unsigned int pending; };
struct delayed_work { struct work_struct work; };
struct mutex { unsigned int locked; };
struct kfifo { u8 data[32]; unsigned int head, count; };
struct tty_port { struct kfifo xmit_fifo; };
struct uart_state { struct tty_port port; };
struct uart_port {
    void *membase;
    struct uart_state *state;
    struct { unsigned int tx, rx, buf_overrun; } icount;
};
struct console { unsigned int unused; };
static unsigned int mmio_reads, mmio_writes, delays, irq_disables;
static unsigned int schedules, cancels, wakeups;
static void *drop_write_to;
static unsigned long jiffies;
static void *system_percpu_wq;
static void udelay(unsigned int n) { delays += n; }
static void writel(u32 v, void *p) {
    mmio_writes++;
    if (p != drop_write_to) memcpy(p, &v, sizeof(v));
}
#define writel_relaxed writel
static u32 readl(void *p) {
    u32 v; mmio_reads++; memcpy(&v, p, sizeof(v)); return v;
}
static void mutex_lock(struct mutex *p) { assert(!p->locked); p->locked = 1; }
static void mutex_unlock(struct mutex *p) { assert(p->locked); p->locked = 0; }
static bool kfifo_get(struct kfifo *q, u8 *v) {
    if (!q->count) return false;
    *v = q->data[q->head++]; q->count--; return true;
}
static unsigned int kfifo_len(struct kfifo *q) { return q->count; }
static bool uart_tx_stopped(struct uart_port *p) { return false; }
static void uart_write_wakeup(struct uart_port *p) { wakeups++; }
static void schedule_work(struct work_struct *p) { p->pending = 1; schedules++; }
static void cancel_work_sync(struct work_struct *p) { p->pending = 0; cancels++; }
static void mod_delayed_work(void *q, struct delayed_work *p, unsigned int delay) {
    p->work.pending = 1; schedules++;
}
static void disable_irq_nosync(int irq) { irq_disables++; }
static u32 jiffies_to_msecs(unsigned long v) { return (u32)v; }

/* Dependencies are defined before their callers in this extracted file. */
#include "actual-functions.inc"

static struct eud_port up;
static struct uart_state state;
static u32 registers[0x2000 / sizeof(u32)], ahb;
static void clear(void) {
    memset(&up, 0, sizeof(up)); memset(&state, 0, sizeof(state));
    memset(registers, 0, sizeof(registers));
    up.port.membase = registers; up.port.state = &state;
    up.ahb2phy_cfg = &ahb; up.original_ahb2phy_cfg = 0x77; ahb = 0x11;
    eud = &up; mmio_reads = mmio_writes = delays = irq_disables = 0;
    schedules = cancels = wakeups = 0; drop_write_to = NULL;
}
static void enqueue(void) {
    memcpy(state.port.xmit_fifo.data, "ABCD", 4);
    state.port.xmit_fifo.count = 4;
}
static void setreg(unsigned int off, u32 v) { registers[off / 4] = v; }

int main(void) {
    unsigned int groups = 0;
    clear(); enqueue();
    eud_tx_work(&up.tx_work);
    assert(up.port.icount.tx == 4 && !state.port.xmit_fifo.count);
    assert(mmio_writes == 6 && up.tx_journal_total == 1);
    assert(up.tx_journal[0].len == 4 && !memcmp(up.tx_journal[0].data, "ABCD", 4));
    groups++; puts("normal actual TX baseline");

    clear(); enqueue(); up.tx_stopping = true;
    eud_tx_work(&up.tx_work);
    assert(up.port.icount.tx == 4 && !state.port.xmit_fifo.count);
    assert(!mmio_writes && !up.tx_journal_total);
    clear(); enqueue(); up.tx_stopping = true;
    eud_shutdown(&up.port);
    assert(cancels == 1 && up.port.icount.tx == 4 && !state.port.xmit_fifo.count);
    assert(!mmio_writes && !up.tx_journal_total);
    assert(eud_tx_empty(&up.port) == TIOCSER_TEMT);
    groups++; puts("tx_stopping cannot preserve queued TTY bytes or prove device ACK");

    clear(); enqueue(); up.tx_stopping = up.rx_stopping = true;
    eud_stop_tx(&up.port); eud_stop_rx(&up.port);
    assert(state.port.xmit_fifo.count == 4 && up.tx_stopping && up.rx_stopping);
    eud_start_tx(&up.port);
    assert(schedules == 1 && up.tx_work.pending);
    assert(eud_startup(&up.port) == 0 && up.tx_stopping && up.rx_stopping);
    groups++; puts("UART stop callbacks are no-ops; start still queues; startup does not restore");

    clear(); up.rx_irq_enabled = up.rx_mask_changed = up.rx_irq_started = true;
    up.rx_irq_waiting = up.rx_console_irq_credit = true;
    up.original_int1_mask = 0x18; setreg(EUD_REG_INT1_EN_MASK, 1);
    eud_rx_irq_stop_locked(&up, 0);
    assert(irq_disables == 1 && !up.rx_irq_enabled && !up.rx_mask_changed);
    assert(!up.rx_irq_waiting && !up.rx_console_irq_credit && up.rx_irq_started);
    assert(registers[EUD_REG_INT1_EN_MASK / 4] == 0x18);
    clear(); up.rx_mask_changed = true; up.original_int1_mask = 0x18;
    setreg(EUD_REG_INT1_EN_MASK, 1);
    drop_write_to = (u8 *)registers + EUD_REG_INT1_EN_MASK;
    eud_rx_irq_stop_locked(&up, 0);
    assert(registers[EUD_REG_INT1_EN_MASK / 4] == 1 && !up.rx_mask_changed);
    groups++; puts("IRQ stop is not synchronization or restart; mask readback is not checked");

    clear(); eud_restore_ahb2phy(&up);
    assert(ahb == 0x77 && mmio_writes == 1 && mmio_reads == 1);
    clear(); drop_write_to = &ahb;
    eud_restore_ahb2phy(&up);
    assert(ahb == 0x11 && mmio_reads == 1); /* void helper reports no error */
    groups++; puts("AHB helper restores probe-era value and cannot report readback mismatch");

    clear(); up.tx_stopping = true; up.rx_irq_started = true;
    setreg(EUD_REG_INT_STATUS_1, 1); setreg(EUD_REG_COM_RX_ID, EUD_RX_UART_ID);
    setreg(EUD_REG_COM_RX_LEN, 1); setreg(EUD_REG_COM_RX_DAT, 0x41);
    eud_console_write_legacy(NULL, "XYZ", 3);
    assert(!mmio_writes && mmio_reads && up.rx_queue_count);
    clear(); up.tx_stopping = up.rx_stopping = up.rx_irq_started = true;
    eud_console_write_legacy(NULL, "XYZ", 3);
    assert(!mmio_reads && !mmio_writes && !schedules);
    groups++; puts("TX-only console gate still consumes RX; both flags suppress FIFO but retain no printk bytes");

    clear(); up.rx_irq_enabled = up.rx_irq_started = true;
    setreg(EUD_REG_COM_RX_ID, EUD_RX_UART_ID); setreg(EUD_REG_COM_RX_LEN, 2);
    assert(eud_rx_collect_locked(&up, 1, EUD_RX_SOURCE_IRQ) == 2);
    assert(up.rx_bootloader_pending && !up.rx_irq_enabled && irq_disables == 1);
    unsigned int before = mmio_reads;
    assert(eud_console_rx_locked(&up) == 0 && mmio_reads == before);
    groups++; puts("already accepted F1 is a separate pending restart, not a restorable RX sample");
    printf("groups=%u\n", groups);
    return groups == 7 ? 0 : 1;
}
