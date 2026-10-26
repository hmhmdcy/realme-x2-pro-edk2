"""Generate an optional returning CSR stage; frozen EUD R2 stays untouched."""
from pathlib import Path
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent
R2 = HERE.parent / 'eud-runtime-window-candidate-r2'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(R2 / 'eud.c') == '1479c3cf0be0b4d62a2b66486b3be5819f28da3d380c95ed76c2a1e6966db3af'
assert sha(R2 / 'eud-com-window.h') == '8003aa9619d2f9d1a15d4ff97460b8f106dc54defc841f31670e98d48e2d8c46'
text = old = (R2 / 'eud.c').read_text()


def replace(before, after):
    global text
    assert text.count(before) == 1, before[:90]
    text = text.replace(before, after)


header = (R2 / 'eud-com-window.h').read_text()
header = header.replace(' * This API suppresses COM software I/O; it never changes CSR/AHB2PHY and does\n * not grant DP/DM, analog high-Z, USB routing or charging permission.',
''' * Software calls suppress COM I/O; the separate explicit CSR stage saves and
 * restores only known 0/1 CSR_EUD_EN values. Neither grants DP/DM, analog
 * high-Z, USB routing or charging permission. AHB2PHY is never borrowed.''')
header = header.replace('        bool csr_touched;\n', '        bool csr_touched;\n        bool hardware_owned;\n')
addition = '''
/* Same-image internal API only. No callback/atomic context or held EUD lock.
 * The caller owns powered MMIO and pre-remove cancellation/join separately.
 * begin requires completed software quiet and a current exact cookie; it
 * consumes one supported CSR borrow per quiet session, including old value 0.
 * restore is explicit, including after cancel; readback failure keeps the
 * hardware owner and prevents quiet_end from resuming producers. A successful
 * retry reports restored while retaining first enter/restore error history;
 * error is this call's result. Removed MMIO can never be restored by this API.
 * disabled_verified attests only the last CSR read, not electrical routing.
 */
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

int eud_com_csr_begin(u64 cookie, struct eud_com_csr_result *result);
int eud_com_csr_restore(u64 cookie, struct eud_com_csr_result *result);
'''
header = header.replace('\n#endif\n', addition + '\n#endif\n')
replace('        u64 window_cookie;\n', '        u64 window_cookie;\n        struct eud_com_csr_result window_csr;\n')
replace('static u64 eud_window_orphan;\n', 'static u64 eud_window_orphan;\nstatic struct eud_com_csr_result eud_csr_orphan;\n')
replace('                .software_quiet = up && up->window_quiet,',
'''                .software_quiet = up && up->window_quiet,
                .csr_touched = up && up->window_csr.csr_touched,
                .hardware_owned = up && up->window_csr.hardware_owned,''')
replace('        up->window_cookie = eud_window_sequence;\n',
'''        up->window_cookie = eud_window_sequence;
        up->window_csr = (struct eud_com_csr_result) {
                .cookie = up->window_cookie,
        };
''')
replace('                if (cancelled)\n                        eud_window_orphan = 0;',
'''                if (cancelled) {
                        eud_window_orphan = 0;
                        /* Acknowledgment releases reprobe only, never repairs
                         * removed MMIO or converts its receipt to restored.
                         */
                        eud_csr_orphan = (struct eud_com_csr_result) { 0 };
                }''')
replace('        else if (up->window_irq_enabled && !up->rx_irq_requested)',
'''        else if (up->window_csr.hardware_owned)
                ret = -EBUSY;
        else if (up->window_irq_enabled && !up->rx_irq_requested)''')
replace('static int eud_window_prepare(struct device *dev)',
        (HERE / 'csr-implementation.inc').read_text() + '\n\nstatic int eud_window_prepare(struct device *dev)')
replace('                up->window_state = EUD_COM_REMOVED;\n',
'''                up->window_state = EUD_COM_REMOVED;
                /* Keep a terminal receipt independently from software orphan
                 * acknowledgment. No access to removed CSR can restore it.
                 */
                eud_csr_orphan = up->window_csr;
                eud_csr_orphan.removed = true;
                eud_csr_orphan.restored = false;
                eud_csr_orphan.software_quiet = true;
                eud_csr_orphan.cancelled = true;
''')
(HERE / 'eud.c').write_bytes(text.encode())
(HERE / 'eud-com-window.h').write_bytes(header.encode())
delta = ''.join(difflib.unified_diff(old.splitlines(True), text.splitlines(True), fromfile='a/drivers/tty/serial/eud.c', tofile='b/drivers/tty/serial/eud.c'))
delta += ''.join(difflib.unified_diff((R2 / 'eud-com-window.h').read_text().splitlines(True), header.splitlines(True), fromfile='a/drivers/tty/serial/eud-com-window.h', tofile='b/drivers/tty/serial/eud-com-window.h'))
(HERE / 'r2-to-csr.patch').write_bytes(delta.encode())

# Preserve the R2 real-function fixture except new declarations and the entire
# actual window+remove section. No hand-written model of CSR control flow.
fixture = (R2 / 'candidate-functions.inc').read_text()
fixture = fixture.replace('        u64 window_cookie;\n', '        u64 window_cookie;\n        struct eud_com_csr_result window_csr;\n')
fixture = fixture.replace('        bool csr_touched;\n', '        bool csr_touched;\n        bool hardware_owned;\n')
csr_struct = addition[addition.index('struct eud_com_csr_result {'):addition.index('\nint eud_com_csr_begin')]
fixture = fixture.replace('struct eud_tx_record {', csr_struct + '\n\nstruct eud_tx_record {')
start = '/* Internal COM software window.'
fstart = fixture.index(start)
tstart = text.index(start)
window = text[tstart:text.index('static int eud_probe_locked(', tstart)].rstrip()
remove = text[text.index('static void eud_remove_locked('):text.index('static const struct of_device_id eud_com_dt_match[]')].rstrip()
fixture = fixture[:fstart] + window + '\n\n' + remove + '\n'
(HERE / 'candidate-functions.inc').write_bytes(fixture.encode())
(HERE / 'build-object.py').write_bytes((R2 / 'build-object.py').read_bytes())
fake = (R2 / 'fake-eud-os.h').read_text()
fake = fake.replace('static bool review_paused,review_release,review_join_waiting,review_begin_done,review_tx_running;',
                    'static bool review_join_waiting,review_tx_running;')
fake = fake.replace('static __thread bool review_writer,review_borrower,review_pause_once;',
                    'static __thread bool review_borrower;')
fake = fake.replace('static void writel(u32 v, void *p) {', 'static void (*csr_write_hook)(u32, void *);\nstatic void writel(u32 v, void *p) { if(csr_write_hook){csr_write_hook(v,p);return;}')
fake = fake.replace('static u32 readl(void *p) {', 'static bool (*csr_read_hook)(void *, u32 *);\nstatic u32 readl(void *p) { u32 injected;if(csr_read_hook&&csr_read_hook(p,&injected))return injected;')
(HERE / 'fake-eud-os.h').write_bytes(fake.encode())
result = {'r2_base_sha256': sha(R2 / 'eud.c'), 'candidate_sha256': sha(HERE / 'eud.c'),
          'header_sha256': sha(HERE / 'eud-com-window.h'), 'delta_sha256': sha(HERE / 'r2-to-csr.patch'),
          'csr_stage_only': True, 'ahb_window_access_added': False,
          'automatic_consumer_present': False, 'r2_modified': False}
(HERE / 'candidate-result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
print(json.dumps(result, indent=2))
