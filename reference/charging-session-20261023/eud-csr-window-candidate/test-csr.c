#include "fake-eud-os.h"
#include "candidate-functions.inc"

static struct eud_port up;
static struct uart_state state;
static struct platform_device device;
static u32 registers[0x2000 / sizeof(u32)], ahb;
static struct eud_com_window_result sw;
static struct eud_com_csr_result hw;
static bool initialized, drop_write, corrupt_write;
static u32 drop_value, corrupt_value;
static unsigned int csr_reads, csr_writes;
static bool pause_csr_write, write_paused, release_write;

static void csr_write(u32 value, void *address)
{
        assert(address == (void *)registers + EUD_REG_CSR_EUD_EN);
        assert(value == 0 || value == 1);
        assert(eud == &up && up.window_quiet);
        csr_writes++; mmio_writes++;
        if (pause_csr_write) {
                pthread_mutex_lock(&review_lock);
                write_paused = true;
                pthread_cond_broadcast(&review_cond);
                while (!release_write)
                        pthread_cond_wait(&review_cond, &review_lock);
                pthread_mutex_unlock(&review_lock);
        }
        if (corrupt_write && value == corrupt_value) {
                u32 bad = value | 2;
                memcpy(address, &bad, sizeof(bad));
        } else if (!drop_write || value != drop_value)
                memcpy(address, &value, sizeof(value));
}

static bool csr_read(void *address, u32 *value)
{
        assert(address == (void *)registers + EUD_REG_CSR_EUD_EN);
        assert(eud == &up && up.window_quiet);
        csr_reads++; mmio_reads++;
        memcpy(value, address, sizeof(*value));
        return true;
}

static void setup(u32 initial)
{
        if (initialized) {
                assert(!pthread_mutex_destroy(&up.port.lock));
                assert(!pthread_mutex_destroy(&up.tx_mutex.lock));
        }
        memset(&up, 0, sizeof(up)); memset(&state, 0, sizeof(state));
        memset(registers, 0, sizeof(registers));
        assert(!pthread_mutex_init(&up.port.lock, NULL));
        assert(!pthread_mutex_init(&up.tx_mutex.lock, NULL));
        initialized = true;
        up.port.membase = registers; up.port.state = &state;
        up.ahb2phy_cfg = &ahb; up.original_ahb2phy_cfg = 0x77; ahb = 0x11;
        up.rx_irq_started = up.rx_irq_requested = up.rx_irq_enabled = true;
        device.dev.data = &up.port; eud = &up;
        eud_reboot_pending = false; eud_window_orphan = 0;
        eud_csr_orphan = (struct eud_com_csr_result) { 0 };
        registers[EUD_REG_CSR_EUD_EN / sizeof(u32)] = initial;
        csr_reads = csr_writes = mmio_reads = mmio_writes = 0;
        irq_disables = irq_enables = irq_syncs = schedules = cancels = 0;
        restarts = uart_removes = frees = 0;
        csr_write_hook = csr_write; csr_read_hook = csr_read;
        drop_write = corrupt_write = pause_csr_write = write_paused = release_write = false;
        review_forbid_mmio = false; review_quiet = NULL;
        review_unregister_hook = review_uart_remove_hook = NULL;
        review_mod_hook = review_unlock_hook = review_enable_hook = NULL;
        review_schedule_hook = NULL; review_tx_mutex = NULL; review_tx_work = NULL;
        review_tx_running = false; stop_at_join = false; test_current_work = NULL;
        assert(!eud_com_quiet_begin(&sw)); assert(sw.software_quiet);
}

static void unchanged(unsigned int reads, unsigned int writes)
{
        assert(reads == csr_reads && writes == csr_writes && ahb == 0x11);
}

static void ok(const char *name) { printf("ok: %s\n", name); }

static void no_consumer(void)
{
        setup(1);
        assert(!eud_com_quiet_end(sw.cookie, &sw));
        assert(sw.restored && !sw.csr_touched && !sw.hardware_owned);
        assert(registers[EUD_REG_CSR_EUD_EN / sizeof(u32)] == 1);
        unchanged(0, 0);
        ok("software-only default has no CSR access");
}

static void enabled_and_tokens(void)
{
        setup(1); u64 cookie = sw.cookie;
        assert(eud_com_csr_begin(cookie + 1, &hw) == -ESTALE);
        assert(eud_com_csr_restore(0, &hw) == -ESTALE);
        assert(!hw.hardware_owned && !hw.saved_valid); unchanged(0, 0);
        assert(!eud_com_csr_begin(cookie, &hw));
        assert(hw.hardware_owned && hw.saved_valid && hw.saved_value == 1);
        assert(hw.disabled_verified && hw.readback_valid && hw.readback == 0);
        assert(hw.csr_touched && !hw.restored); unchanged(2, 1);
        assert(eud_com_csr_begin(cookie, &hw) == -EALREADY); unchanged(2, 1);
        unsigned int enables = irq_enables, queued = schedules;
        assert(eud_com_quiet_end(cookie, &sw) == -EBUSY);
        assert(sw.hardware_owned && sw.software_quiet && !sw.restored);
        assert(irq_enables == enables && schedules == queued); unchanged(2, 1);
        assert(!eud_com_csr_restore(cookie, &hw));
        assert(hw.restored && !hw.hardware_owned && hw.saved_value == 1);
        assert(!hw.disabled_verified && hw.readback == 1); unchanged(4, 2);
        assert(eud_com_csr_restore(cookie, &hw) == -EALREADY);
        assert(eud_com_csr_begin(cookie, &hw) == -EALREADY); unchanged(4, 2);
        assert(!eud_com_quiet_end(cookie, &sw)); assert(sw.restored);
        ok("known enabled CSR exact restore, stale/duplicate zero-write and quiet_end fence");
}

static void disabled_values(void)
{
        setup(0); u64 cookie = sw.cookie;
        assert(!eud_com_csr_begin(cookie, &hw));
        assert(hw.hardware_owned && hw.saved_value == 0 && !hw.csr_touched);
        unchanged(1, 0);
        assert(!eud_com_csr_restore(cookie, &hw));
        assert(hw.restored && hw.disabled_verified && !hw.csr_touched);
        unchanged(2, 0); assert(!eud_com_quiet_end(cookie, &sw));

        setup(0); cookie = sw.cookie;
        assert(!eud_com_csr_begin(cookie, &hw));
        registers[EUD_REG_CSR_EUD_EN / sizeof(u32)] = 1;
        assert(!eud_com_csr_restore(cookie, &hw));
        assert(hw.saved_value == 0 && hw.readback == 0 && hw.csr_touched);
        unchanged(3, 1); assert(!eud_com_quiet_end(cookie, &sw));
        ok("known disabled CSR borrowed without entry write and restores actual old zero");
}

static void unsupported_value(void)
{
        setup(2); u64 cookie = sw.cookie;
        assert(eud_com_csr_begin(cookie, &hw) == -EOPNOTSUPP);
        assert(hw.readback_valid && hw.readback == 2 && !hw.saved_valid);
        assert(!hw.hardware_owned && !hw.csr_touched && hw.enter_error == -EOPNOTSUPP);
        unchanged(1, 0);
        assert(eud_com_csr_restore(cookie, &hw) == -EALREADY); unchanged(1, 0);
        assert(!eud_com_quiet_end(cookie, &sw));
        assert(registers[EUD_REG_CSR_EUD_EN / sizeof(u32)] == 2);
        ok("unsupported whole CSR value is one read, no write and no hardware owner");
}

static void enter_failure(void)
{
        setup(1); u64 cookie = sw.cookie;
        drop_write = true; drop_value = 0;
        assert(eud_com_csr_begin(cookie, &hw) == -EIO);
        assert(hw.hardware_owned && hw.saved_value == 1 && !hw.disabled_verified);
        assert(hw.enter_error == -EIO && !hw.restore_error); unchanged(2, 1);
        assert(eud_com_quiet_end(cookie, &sw) == -EBUSY);
        drop_write = false;
        /* Failed entry left actual 1: restoration verifies it, no extra write. */
        assert(!eud_com_csr_restore(cookie, &hw)); unchanged(3, 1);
        assert(hw.restored && hw.enter_error == -EIO && !hw.restore_error);
        assert(!eud_com_quiet_end(cookie, &sw));
        setup(1); cookie = sw.cookie; corrupt_write = true; corrupt_value = 0;
        assert(eud_com_csr_begin(cookie, &hw) == -EIO);
        assert(hw.readback == 2 && hw.saved_value == 1 && hw.hardware_owned);
        corrupt_write = false;
        assert(!eud_com_csr_restore(cookie, &hw));
        assert(hw.readback == 1 && hw.restored && hw.enter_error == -EIO);
        unchanged(4, 2); assert(!eud_com_quiet_end(cookie, &sw));
        ok("entry mismatch retains owner and primary error until explicit verified restoration");
}

static void restore_failure_cancel(void)
{
        setup(1); u64 cookie = sw.cookie;
        assert(!eud_com_csr_begin(cookie, &hw));
        corrupt_write = true; corrupt_value = 1;
        assert(eud_com_csr_restore(cookie, &hw) == -EIO);
        assert(hw.hardware_owned && !hw.restored && hw.restore_error == -EIO);
        assert(hw.readback == 3 && !hw.enter_error); unchanged(4, 2);
        unsigned int enables = irq_enables, queued = schedules;
        assert(!eud_com_quiet_cancel(cookie, &sw));
        assert(sw.cancelled && sw.hardware_owned); unchanged(4, 2);
        assert(eud_com_csr_begin(cookie, &hw) == -ECANCELED); unchanged(4, 2);
        assert(eud_com_quiet_end(cookie, &sw) == -EBUSY);
        assert(irq_enables == enables && schedules == queued);
        corrupt_write = false;
        assert(!eud_com_csr_restore(cookie, &hw));
        assert(hw.restored && hw.cancelled && !hw.hardware_owned);
        assert(hw.restore_error == -EIO && hw.error == 0); unchanged(6, 3);
        assert(!eud_com_quiet_end(cookie, &sw));
        assert(sw.cancelled && sw.restored && sw.error == -ECANCELED);
        ok("restore mismatch stays quiet, cancel never reconnects, explicit retry retains diagnostics");
}

static void preconditions(void)
{
        setup(1); u64 cookie = sw.cookie;
        assert(eud_com_csr_begin(cookie, NULL) == -EINVAL);
        assert(eud_com_csr_restore(cookie, NULL) == -EINVAL);
        up.window_system_pm = true;
        assert(eud_com_csr_begin(cookie, &hw) == -EHOSTDOWN);
        up.window_system_pm = false; up.window_runtime_pm = true;
        assert(eud_com_csr_begin(cookie, &hw) == -EHOSTDOWN);
        up.window_runtime_pm = false; eud_reboot_pending = true;
        assert(eud_com_csr_begin(cookie, &hw) == -ESHUTDOWN);
        eud_reboot_pending = false; up.rx_bootloader_pending = true;
        assert(eud_com_csr_begin(cookie, &hw) == -ESHUTDOWN);
        up.rx_bootloader_pending = false; up.rx_stopping = true;
        assert(eud_com_csr_begin(cookie, &hw) == -ESHUTDOWN);
        up.rx_stopping = false; up.tx_stopping = true;
        assert(eud_com_csr_begin(cookie, &hw) == -ESHUTDOWN);
        up.tx_stopping = false; test_current_work = &up.tx_work;
        assert(eud_com_csr_begin(cookie, &hw) == -EDEADLK);
        test_current_work = NULL; up.window_state = EUD_COM_QUIETING;
        assert(eud_com_csr_begin(cookie, &hw) == -EBUSY);
        up.window_state = EUD_COM_QUIET; unchanged(0, 0);
        assert(!eud_com_csr_begin(cookie, &hw));
        assert(eud_window_prepare(&device.dev) == -EBUSY);
        assert(eud_window_runtime_suspend(&device.dev) == -EBUSY);
        eud_reboot_cmd(&up, 2); assert(!restarts && !eud_reboot_pending);
        up.window_system_pm = true;
        assert(eud_com_csr_restore(cookie, &hw) == -EHOSTDOWN);
        assert(hw.hardware_owned && !hw.restored); unchanged(2, 1);
        up.window_system_pm = false;
        assert(!eud_com_csr_restore(cookie, &hw));
        assert(!eud_com_quiet_end(cookie, &sw));
        assert(eud_com_csr_begin(cookie, &hw) == -ESTALE); unchanged(4, 2);
        ok("PM, F1, stopping, self-work and incomplete quiet preconditions reject without CSR access");
}

static u64 race_cookie;
static struct eud_com_csr_result begin_result;
static struct eud_com_window_result end_result;
static int end_ret;
static void *begin_thread(void *unused)
{
        assert(!eud_com_csr_begin(race_cookie, &begin_result)); return NULL;
}
static void *end_thread(void *unused)
{
        end_ret = eud_com_quiet_end(race_cookie, &end_result); return NULL;
}
static void *remove_thread(void *unused) { eud_remove(&device); return NULL; }
static void wait_write(void)
{
        struct timespec deadline; clock_gettime(CLOCK_REALTIME, &deadline); deadline.tv_sec += 3;
        assert(!pthread_mutex_lock(&review_lock));
        while (!write_paused)
                assert(!pthread_cond_timedwait(&review_cond, &review_lock, &deadline));
        assert(!pthread_mutex_unlock(&review_lock));
        /* The actual CSR function, not a fake lock model, owns the mutex. */
        assert(pthread_mutex_trylock(&eud_window_lock.lock) == EBUSY);
}
static void release_writer(void)
{
        assert(!pthread_mutex_lock(&review_lock)); release_write = true;
        pthread_cond_broadcast(&review_cond); assert(!pthread_mutex_unlock(&review_lock));
}

static void quiet_end_race(void)
{
        setup(1); race_cookie = sw.cookie; pause_csr_write = true;
        pthread_t enter, end;
        assert(!pthread_create(&enter, NULL, begin_thread, NULL)); wait_write();
        assert(!pthread_create(&end, NULL, end_thread, NULL));
        release_writer(); assert(!pthread_join(enter, NULL)); assert(!pthread_join(end, NULL));
        assert(end_ret == -EBUSY && end_result.software_quiet && !end_result.restored);
        assert(!irq_enables && !schedules); pause_csr_write = false;
        assert(!eud_com_csr_restore(race_cookie, &hw));
        assert(!eud_com_quiet_end(race_cookie, &sw));
        ok("concurrent quiet_end cannot resume producers across an in-progress CSR entry");
}

static void removal_race(void)
{
        setup(1); race_cookie = sw.cookie; pause_csr_write = true;
        pthread_t enter, remove;
        assert(!pthread_create(&enter, NULL, begin_thread, NULL)); wait_write();
        assert(!pthread_create(&remove, NULL, remove_thread, NULL));
        release_writer(); assert(!pthread_join(enter, NULL)); assert(!pthread_join(remove, NULL));
        assert(!eud && !device.dev.data && eud_window_orphan == race_cookie);
        assert(registers[EUD_REG_CSR_EUD_EN / sizeof(u32)] == 0 && ahb == 0x11);
        assert(!up.rx_work.work.pending && !up.tx_work.pending);
        unsigned int reads = csr_reads, writes = csr_writes;
        assert(eud_com_csr_restore(race_cookie, &hw) == -ENODEV);
        assert(hw.removed && hw.hardware_owned && hw.saved_valid && hw.saved_value == 1);
        assert(!hw.restored && hw.disabled_verified); unchanged(reads, writes);
        assert(eud_com_quiet_end(race_cookie + 1, &sw) == -ENODEV);
        assert(eud_window_orphan == race_cookie && !sw.restored);
        assert(eud_com_quiet_end(race_cookie, &sw) == -ENODEV);
        assert(!eud_window_orphan && !sw.restored);
        assert(eud_com_csr_restore(race_cookie, &hw) == -ENODEV);
        assert(hw.removed && !hw.restored); unchanged(reads, writes);
        u64 old_cookie = race_cookie;
        setup(1);
        assert(sw.cookie != old_cookie);
        assert(eud_com_csr_restore(old_cookie, &hw) == -ESTALE);
        assert(!hw.saved_valid && !hw.hardware_owned); unchanged(0, 0);
        assert(!eud_com_quiet_end(sw.cookie, &sw));
        ok("remove serializes CSR, preserves a terminal receipt, orphan ack never restores old MMIO");
}

int main(void)
{
        no_consumer(); enabled_and_tokens(); disabled_values(); unsupported_value();
        enter_failure(); restore_failure_cancel(); preconditions(); quiet_end_race(); removal_race();
        return 0;
}
