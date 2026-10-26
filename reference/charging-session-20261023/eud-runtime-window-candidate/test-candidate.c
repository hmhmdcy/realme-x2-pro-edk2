#include "fake-eud-os.h"
#include "candidate-functions.inc"

static struct eud_port up;
static struct uart_state state;
static struct platform_device device;
static u32 registers[0x2000 / sizeof(u32)], ahb;
static bool initialized;
static void clear(void) {
    if (initialized) {
        pthread_mutex_destroy(&up.port.lock);
        pthread_mutex_destroy(&up.tx_mutex.lock);
    }
    memset(&up, 0, sizeof(up)); memset(&state, 0, sizeof(state));
    memset(registers, 0, sizeof(registers));
    pthread_mutex_init(&up.port.lock, NULL); pthread_mutex_init(&up.tx_mutex.lock, NULL);
    initialized = true;
    up.port.membase = registers; up.port.state = &state;
    up.ahb2phy_cfg = &ahb; up.original_ahb2phy_cfg = 0x77; ahb = 0x11;
    up.rx_irq_started = true; device.dev.data = &up.port;
    eud = &up; eud_reboot_pending = false; eud_window_orphan = 0;
    mmio_reads = mmio_writes = irq_disables = irq_enables = irq_syncs = 0;
    schedules = cancels = restarts = uart_removes = frees = 0;
    stop_at_join = join_reached = join_released = false;
    test_current_work = NULL;
}
static void enqueue(void) {
    memcpy(state.port.xmit_fifo.data, "ABCD", 4); state.port.xmit_fifo.count = 4;
}
static struct eud_com_window_result r;
static void quiet(void) { assert(!eud_com_quiet_begin(&r)); assert(r.software_quiet); }
static void *begin_thread(void *unused) { quiet(); return NULL; }
static void *remove_thread(void *unused) { eud_remove(&device); return NULL; }

int main(void) {
    unsigned int groups = 0;
    clear(); enqueue();
    eud_tx_work(&up.tx_work);
    assert(up.port.icount.tx == 4 && mmio_writes == 6 && up.tx_journal_total == 1);
    assert(eud_startup(&up.port) == 0 && eud_tx_empty(&up.port) == TIOCSER_TEMT);
    eud_stop_tx(&up.port); eud_stop_rx(&up.port);
    groups++; puts("no consumer: baseline TX/startup/UART callbacks retained");

    clear(); enqueue(); up.rx_irq_enabled = up.rx_irq_requested = true;
    up.tx_work.pending = up.rx_work.work.pending = 1;
    quiet(); u64 cookie = r.cookie;
    assert(cookie && r.state == EUD_COM_QUIET && irq_disables == 1 && irq_syncs == 1);
    assert(cancels == 2 && !up.tx_work.pending && !up.rx_work.work.pending);
    assert(!mmio_reads && !mmio_writes && !r.csr_touched && !r.ahb2phy_touched);
    assert(eud_com_quiet_begin(&r) == -EBUSY && !r.cookie);
    eud_start_tx(&up.port); eud_tx_work(&up.tx_work); eud_shutdown(&up.port);
    eud_console_write_legacy(NULL, "log", 3); eud_rx_irq(1, &up);
    eud_rx_work(&up.rx_work.work); eud_reboot_cmd(&up, 2);
    assert(eud_startup(&up.port) == -EBUSY && state.port.xmit_fifo.count == 4);
    assert(!up.port.icount.tx && !mmio_reads && !mmio_writes && !schedules && !restarts);
    groups++; puts("quiet joins IRQ/work and gates TX/shutdown/startup/console/IRQ/RX/reboot");

    assert(eud_com_quiet_end(cookie + 1, &r) == -ESTALE && !irq_enables && up.window_quiet);
    assert(!eud_com_quiet_end(cookie, &r) && r.restored && !r.software_quiet);
    assert(up.rx_irq_enabled && irq_enables == 1 && up.tx_work.pending && up.rx_work.work.pending);
    assert(!mmio_reads && !mmio_writes && ahb == 0x11);
    assert(eud_com_quiet_end(cookie, &r) == -ESTALE);
    groups++; puts("only the exact token restores saved enabled IRQ and pending TTY/RX");

    clear(); up.rx_irq_fault = EUD_IRQ_FAULT_WATCHDOG; quiet(); cookie = r.cookie;
    assert(!eud_com_quiet_cancel(cookie, &r) && r.cancelled && !r.restored);
    assert(!irq_enables && up.window_quiet && r.error == -ECANCELED);
    assert(!eud_com_quiet_end(cookie, &r) && r.restored && r.cancelled && r.error == -ECANCELED);
    assert(!irq_enables && !up.rx_irq_enabled && up.rx_irq_fault == EUD_IRQ_FAULT_WATCHDOG);
    groups++; puts("cancel holds quiet; explicit end preserves disabled IRQ and old fault");

    clear(); up.rx_bootloader_pending = true;
    assert(eud_com_quiet_begin(&r) == -ESHUTDOWN && !up.window_quiet);
    up.rx_bootloader_pending = false; eud_reboot_pending = true;
    assert(eud_com_quiet_begin(&r) == -ESHUTDOWN);
    eud_reboot_pending = false; up.rx_irq_started = false;
    assert(eud_com_quiet_begin(&r) == -EAGAIN);
    up.rx_irq_started = true; up.tx_stopping = true;
    assert(eud_com_quiet_begin(&r) == -ESHUTDOWN);
    up.tx_stopping = false; test_current_work = &up.rx_work.work;
    assert(eud_com_quiet_begin(&r) == -EDEADLK);
    test_current_work = &up.tx_work;
    assert(eud_com_quiet_begin(&r) == -EDEADLK);
    test_current_work = NULL;
    assert(!mmio_reads && !mmio_writes);
    groups++; puts("F1/reboot/stopping/startup state cannot be silently cleared by begin");

    clear(); quiet(); cookie = r.cookie;
    assert(eud_window_pm_ops.prepare(&device.dev) == -EBUSY);
    assert(eud_window_pm_ops.runtime_suspend(&device.dev) == -EBUSY);
    assert(!eud_com_quiet_end(cookie, &r));
    assert(!eud_window_pm_ops.prepare(&device.dev));
    assert(eud_com_quiet_begin(&r) == -EHOSTDOWN);
    eud_window_pm_ops.complete(&device.dev);
    assert(!eud_window_pm_ops.runtime_suspend(&device.dev));
    assert(eud_com_quiet_begin(&r) == -EHOSTDOWN);
    assert(!eud_window_pm_ops.runtime_resume(&device.dev));
    quiet(); cookie = r.cookie;
    assert(!eud_com_quiet_end(cookie, &r) && !mmio_writes && !mmio_reads);
    groups++; puts("PM rejects quiet; successful prepare blocks new begin through complete");

    clear(); up.rx_irq_enabled = up.rx_irq_requested = true; quiet(); cookie = r.cookie;
    up.rx_irq_requested = false;
    assert(eud_com_quiet_end(cookie, &r) == -ENXIO && r.restore_error == -ENXIO);
    assert(!r.restored && up.window_quiet && !irq_enables);
    up.rx_irq_requested = true;
    assert(!eud_com_quiet_end(cookie, &r));
    groups++; puts("inconsistent IRQ restore refuses, retains token and can be explicitly retried");

    clear(); quiet(); cookie = r.cookie; eud_remove(&device);
    assert(!eud && !device.dev.data && uart_removes == 1 && ahb == 0x11);
    assert(eud_window_orphan == cookie && !mmio_reads && !mmio_writes);
    assert(eud_com_quiet_end(cookie + 1, &r) == -ENODEV && eud_window_orphan == cookie);
    assert(eud_com_quiet_end(cookie, &r) == -ENODEV && !eud_window_orphan && !r.restored && r.cancelled);
    clear(); eud_remove(&device);
    assert(ahb == 0x77 && mmio_writes == 1 && mmio_reads == 1);
    groups++; puts("remove invalidates token, preserves borrowed AHB; ordinary remove behavior retained");

    clear(); stop_at_join = true;
    pthread_t a, b;
    assert(!pthread_create(&a, NULL, begin_thread, NULL));
    pthread_mutex_lock(&barrier_lock);
    while (!join_reached) pthread_cond_wait(&barrier_cond, &barrier_lock);
    assert(up.window_quiet && up.window_state == EUD_COM_QUIETING);
    assert(!pthread_create(&b, NULL, remove_thread, NULL));
    /* The global lifetime lock remains owned across the join. */
    assert(pthread_mutex_trylock(&eud_window_lock.lock) == EBUSY);
    join_released = true; pthread_cond_broadcast(&barrier_cond);
    pthread_mutex_unlock(&barrier_lock);
    pthread_join(a, NULL); pthread_join(b, NULL);
    assert(!eud && up.window_state == EUD_COM_REMOVED && eud_window_orphan == r.cookie);
    assert(eud_com_quiet_end(r.cookie, &r) == -ENODEV && !eud_window_orphan);
    assert(ahb == 0x11 && !mmio_reads && !mmio_writes);
    groups++; puts("actual begin join and remove serialize through one object-lifetime mutex");

    assert(eud_com_quiet_begin(NULL) == -EINVAL && eud_com_quiet_end(0, NULL) == -EINVAL);
    printf("groups=%u\n", groups);
    return groups == 9 ? 0 : 1;
}
