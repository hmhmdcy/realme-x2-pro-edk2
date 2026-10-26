"""Apply a narrowly scoped EUD nbcon conversion to the verified #140 tree."""
from pathlib import Path
import difflib
import hashlib
import json
import subprocess

root = Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel143')
out = Path('/mnt/e/edk2-samurai-out/kernel143')
source = root/'drivers/tty/serial/eud.c'
assert not out.exists()
assert hashlib.sha256(root.joinpath('arch/arm64/boot/Image').read_bytes()).hexdigest() == '2b244772eb7e15ce587722cd3fed37f775a05d4562a4ac2e6b80701aeb04dc45'
before = source.read_text()
assert 'eud_console_write_thread' not in before and '.cons' not in before
out.mkdir(mode=0o700)
out.joinpath('eud-before-private.c').write_text(before)
out.joinpath('config-before-private').write_bytes(root.joinpath('.config').read_bytes())
with out.joinpath('source-diff-before-private.patch').open('w') as file:
    subprocess.run(['git','-C',str(root),'diff','--binary'],stdout=file,check=True)
text = before.replace('#include <linux/module.h>','#include <linux/module.h>\n#include <linux/mutex.h>')
text = text.replace('        struct work_struct tx_work;','        struct work_struct tx_work;\n        struct mutex tx_mutex;')
assert text.count('        tport = &port->state->port;') == 2
text = text.replace('        tport = &port->state->port;','        tport = &port->state->port;\n        mutex_lock(&up->tx_mutex);')
text = text.replace('        if (kfifo_len(&tport->xmit_fifo) < WAKEUP_CHARS)',
    '        mutex_unlock(&up->tx_mutex);\n\n        if (kfifo_len(&tport->xmit_fifo) < WAKEUP_CHARS)')
text = text.replace('static void eud_console_write(struct console *co, const char *s,',
    'static void eud_console_write_legacy(struct console *co, const char *s,')
needle = '        }\n}\n\nstatic void eud_set_termios'
assert needle in text
text = text.replace(needle,'        }\n        mutex_unlock(&up->tx_mutex);\n}\n\nstatic void eud_set_termios')
callbacks = '''/*
 * Normal printing is serialized with TTY TX by a mutex, while the port lock
 * protects just one complete FIFO frame and its RX collection. Keep the
 * measured pacing: speeding up MMIO loses whole frames on this board.
 *
 * The UART driver deliberately has no .cons association: the EUD console is
 * registered manually after probe. Port operations use their existing lock;
 * normal console/TTY writers also share tx_mutex. No non-printing UART path
 * tries to acquire a second nbcon NORMAL context while this writer owns it.
 */
static void eud_console_device_lock(struct console *co, unsigned long *flags)
{
\tmutex_lock(&eud->tx_mutex);
\tmigrate_disable();
\t*flags = 0;
}

static void eud_console_device_unlock(struct console *co, unsigned long flags)
{
\tmigrate_enable();
\tmutex_unlock(&eud->tx_mutex);
}

static void eud_console_write_thread(struct console *co,
\t\t\t\t     struct nbcon_write_context *wctxt)
{
\tstruct eud_port *up = eud;
\tunsigned int offset = 0;
\tbool kick = false, collect = true;

\twhile (offset < wctxt->len) {
\t\tunsigned long flags;
\t\tunsigned int n;
\t\tbool owned;
\t\tint ret;

\t\tuart_port_lock_irqsave(&up->port, &flags);
\t\tif (!nbcon_enter_unsafe(wctxt)) {
\t\t\tuart_port_unlock_irqrestore(&up->port, flags);
\t\t\tbreak;
\t\t}

\t\tif (!offset) {
\t\t\tret = eud_console_rx_locked(up);
\t\t\tkick = ret != 0;
\t\t\tcollect = ret >= 0;
\t\t}

\t\tn = min_t(unsigned int, wctxt->len - offset, EUD_TX_CHUNK);
\t\teud_send_frame(&up->port, (const u8 *)wctxt->outbuf + offset,
\t\t\t       n, EUD_TX_SOURCE_CONSOLE);
\t\toffset += n;
\t\tif (collect) {
\t\t\tret = eud_console_rx_locked(up);
\t\t\tkick |= ret != 0;
\t\t\tcollect = ret >= 0;
\t\t}

\t\towned = nbcon_exit_unsafe(wctxt);
\t\tuart_port_unlock_irqrestore(&up->port, flags);
\t\tif (!owned)
\t\t\tbreak;
\t\tcond_resched();
\t}

\tif (kick && !READ_ONCE(up->rx_stopping))
\t\tmod_delayed_work(system_percpu_wq, &up->rx_work, 0);
}

/*
 * The old atomic writer is retained only for final panic flushing. It takes
 * the port lock and can hold IRQs off for an entire record, so it must never
 * be advertised as a safe atomic nbcon callback or used for normal printk.
 */
static void eud_console_write_atomic(struct console *co,
\t\t\t\t     struct nbcon_write_context *wctxt)
{
\tif (!nbcon_enter_unsafe(wctxt))
\t\treturn;
\teud_console_write_legacy(co, wctxt->outbuf, wctxt->len);
\tnbcon_exit_unsafe(wctxt);
}

'''
text = text.replace('static struct console eud_console = {', callbacks+'static struct console eud_console = {')
text = text.replace('        .write  = eud_console_write,',
    '\t.write_thread = eud_console_write_thread,\n\t.write_atomic = eud_console_write_atomic,\n\t.device_lock = eud_console_device_lock,\n\t.device_unlock = eud_console_device_unlock,')
text = text.replace('        .flags  = CON_PRINTBUFFER,','\t.flags = CON_PRINTBUFFER | CON_NBCON | CON_NBCON_ATOMIC_UNSAFE,')
text = text.replace('        spin_lock_init(&port->lock);',
    '        spin_lock_init(&port->lock);\n        mutex_init(&up->tx_mutex);')
text = text.replace('        struct mutex tx_mutex;', '\tstruct mutex tx_mutex;')
for line in ['mutex_lock(&up->tx_mutex);','mutex_unlock(&up->tx_mutex);','mutex_init(&up->tx_mutex);']:
    text = text.replace('        '+line, '\t'+line)
assert text.count('mutex_lock(&up->tx_mutex)') == 2 and text.count('mutex_unlock(&up->tx_mutex)') == 2
assert text.count('mutex_lock(&eud->tx_mutex)') == 1
source.write_text(text)
patch = ''.join(difflib.unified_diff(before.splitlines(keepends=True),text.splitlines(keepends=True),
    fromfile='a/drivers/tty/serial/eud.c',tofile='b/drivers/tty/serial/eud.c'))
ref.joinpath('eud-threaded-console.patch').write_text(patch)
out.joinpath('eud-candidate-private.c').write_text(text)
report = dict(stage=143, baseline_kernel_build=140, current_phone_kernel_build=140,
    baseline_image_sha256='2b244772eb7e15ce587722cd3fed37f775a05d4562a4ac2e6b80701aeb04dc45',
    baseline_source_sha256=hashlib.sha256(before.encode()).hexdigest(),
    candidate_source_sha256=hashlib.sha256(text.encode()).hexdigest(),
    normal_nbcon_threaded=True, normal_frame_critical_section=True,
    fifo_pacing_and_rx_collector_unchanged=True, tty_shutdown_serialized_with_normal_console=True,
    legacy_atomic_callback_panic_unsafe_only=True, manual_console_registration_preserved=True,
    driver_cons_association_absent=True, kernel_build_completed=False,
    actual_functions_tested=False, deployed=False, goal_complete=False)
ref.joinpath('source-preparation-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('K143_VERIFIED140_SOURCE_BACKUP_AND_EUD_THREAD_CANDIDATE_PREPARED')
