"""Promote actual host model evidence; generate bounded diagnostics off-tree."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil

R = Path(__file__).resolve().parent
P = Path('/mnt/e/edk2-samurai-out/kernel234')
K = Path('/home/cy122/pmos-samurai-kernel136/kernel')
sha = lambda data: hashlib.sha256(data).hexdigest()
model = json.loads((P / 'rts-mode-contract-validation.json').read_text())
assert model['results'] == {
    'current': {'cases': 16, 'contract_mismatches': 2},
    'proposed_sync_at_end': {'cases': 16, 'contract_mismatches': 0},
    'wrong_sync_before_mode_update': {'cases': 16, 'contract_mismatches': 2}}
assert model['asan_ubsan_passed'] and model['stage'] == 205
assert sha((K / 'drivers/tty/serial/qcom_geni_serial.c').read_bytes()) == model['source_geni_sha256']
assert sha((K / 'drivers/tty/serial/serial_core.c').read_bytes()) == model['source_core_sha256']
assert '#define TIOCM_LOOP\t0x8000' in (K / 'include/uapi/asm-generic/termios.h').read_text()
model.update(stage=234, inherited_report_stage_label_corrected_from=205,
             original205_compile_failure_preserved=True,
             actual_kernel_uapi_tiocm_loop=32768,
             register_bank_modeled=True, locking_stubbed=True,
             naked_sync_call_not_a_deployable_patch=True,
             set_termios_and_set_mctrl_lock_contracts_differ=True)
model.pop('register_bank_and_locking_modeled')
(R / 'rts-mode-contract-validation.json').write_text(json.dumps(model, indent=2) + '\n')
script = (P / 'test-rts-mode-contract-private.py').read_text()
assert "stage=205" in script
script = script.replace("out=Path('/mnt/e/edk2-samurai-out/kernel234/rts-contract-r1')",
                        "out=Path('/mnt/e/edk2-samurai-out/kernel234/rts-contract-reproduction')")
script = script.replace('stage=205', 'stage=234').replace(
    'register_bank_and_locking_modeled=True', 'register_bank_modeled=True,locking_stubbed=True')
script = script.replace("here=Path('/mnt/e/edk2-samurai-out/kernel234')", "here=Path(__file__).resolve().parent")
script = script.replace("(here/'rts-mode-contract-validation.json')", "(out/'validation.json')")
(R / 'test-rts-mode-contract.py').write_text(script)

source = K / 'drivers/bluetooth/hci_qca.c'
old = source.read_bytes()
assert sha(old) == '645ded4980918a2d0a22dd2d56327bbc69c08e3689e9d313158f0d263e291d90'
text = old.decode()


def replace(before, after):
    global text
    assert text.count(before) == 1, (before, text.count(before))
    text = text.replace(before, after)


replace('#include <linux/module.h>', '#include <linux/module.h>\n#include <linux/timekeeping.h>')
replace('enum qca_rx_phase {', '''/* Private diagnostics: no parser repair or additional wire commands. */
#define QCA_RX_DIAG_BUDGET 16
static bool samurai_rx_diag;
module_param(samurai_rx_diag, bool, 0600);
MODULE_PARM_DESC(samurai_rx_diag, "Bounded private baud-change RX diagnostics");

enum qca_rx_phase {''')
replace('\tu32 requested_baudrate;', '''\tu32 requested_baudrate;
\tatomic_t diag_rx_seq;
\tatomic_t diag_budget;''')
replace('\tatomic_set(&qca->pulse_rx_nuls, 0);', '''\tatomic_set(&qca->pulse_rx_nuls, 0);
\tatomic_set(&qca->diag_rx_seq, 0);
\tatomic_set(&qca->diag_budget, QCA_RX_DIAG_BUDGET);''')
replace('''\tint nuls = 0;

\tif (!test_bit(HCI_UART_REGISTERED, &hu->flags))
\t\treturn -EUNATCH;
''', '''\tint nuls = 0;
\tbool diag = false, had_skb = false;
\tu32 seq = 0, phase = 0, expect = 0, baud = 0;
\tbool drop = false;
\tu8 type = 0, padding = 0;
\tu64 timestamp = 0;

\tif (!test_bit(HCI_UART_REGISTERED, &hu->flags))
\t\treturn -EUNATCH;

\tif (READ_ONCE(samurai_rx_diag)) {
\t\tseq = (u32)atomic_inc_return(&qca->diag_rx_seq);
\t\tphase = READ_ONCE(qca->rx_phase);
\t\tif (phase == QCA_RX_BAUDRATE_CHANGE &&
\t\t    atomic_dec_if_positive(&qca->diag_budget) >= 0) {
\t\t\tdiag = true;
\t\t\ttimestamp = ktime_get_mono_fast_ns();
\t\t\tbaud = READ_ONCE(qca->requested_baudrate);
\t\t\tdrop = test_bit(QCA_DROP_VENDOR_EVENT, &qca->flags);
\t\t\thad_skb = !!qca->rx_skb;
\t\t\tpadding = hu->padding;
\t\t\tif (had_skb) {
\t\t\t\ttype = hci_skb_pkt_type(qca->rx_skb);
\t\t\t\texpect = hci_skb_expect(qca->rx_skb);
\t\t\t}
\t\t}
\t}
''')
replace('''\tqca->rx_skb = h4_recv_buf(hu, qca->rx_skb, buffer, count,
\t\t\t\t  qca_recv_pkts, ARRAY_SIZE(qca_recv_pkts));
''', '''\tqca->rx_skb = h4_recv_buf(hu, qca->rx_skb, buffer, count,
\t\t\t\t  qca_recv_pkts, ARRAY_SIZE(qca_recv_pkts));
\tif (diag) {
\t\tbool post_skb = !IS_ERR_OR_NULL(qca->rx_skb);
\t\tint err = IS_ERR(qca->rx_skb) ? PTR_ERR(qca->rx_skb) : 0;
\t\tunsigned int length = count > 0 ? min_t(int, count, 32) : 0;
\t\tu32 post_len = post_skb ? qca->rx_skb->len : 0;
\t\tu32 post_type = post_skb ? hci_skb_pkt_type(qca->rx_skb) : 0;
\t\tu32 post_expect = post_skb ? hci_skb_expect(qca->rx_skb) : 0;
\t\tu8 post_padding = hu->padding;

\t\tbt_dev_info(hu->hdev,
\t\t\t    "RXDIAG234 seq=%u ns=%llu phase=%u baud=%u drop=%u had_skb=%u len=%u type=%u expect=%u padding=%u count=%d skipped=%d err=%d",
\t\t\t    seq, timestamp, phase, baud, drop, had_skb,
\t\t\t    partial, type, expect, padding, count, nuls, err);
\t\tbt_dev_info(hu->hdev,
\t\t\t    "RXDIAG234 seq=%u post_skb=%u len=%u type=%u expect=%u padding=%u head=%*ph",
\t\t\t    seq, post_skb, post_len, post_type, post_expect,
\t\t\t    post_padding, length, buffer);
\t}
''')
candidate = R / 'hci_qca.c'
if candidate.exists():
    assert sha(candidate.read_bytes()) == '851f4495a87311593ab60ec9ee74e918e0ad0608ec0aa8926dc38dc06d6f7458'
candidate.write_text(text)
(R / 'qca-bounded-rx-state.patch').write_text(''.join(difflib.unified_diff(
    old.decode().splitlines(True), text.splitlines(True),
    fromfile='a/drivers/bluetooth/hci_qca.c', tofile='b/drivers/bluetooth/hci_qca.c')))
# Copy only the latest authenticated endpoint; do not discover or change the phone.
shutil.copyfile(P.parent / 'kernel233/usb-ipv6-candidates-private.json',
                P / 'usb-ipv6-candidates-private.json')
for name in ['hci_h4.c', 'hci_uart.h']:
    data = (K / 'drivers/bluetooth' / name).read_bytes()
    (P / name).write_bytes(data)
report = dict(stage=234, source_before_sha256=sha(old), source_after_sha256=sha(candidate.read_bytes()),
              diagnostics_default_disabled=True, phase5_only=True,
              per_qca_open_budget_chunks=16, bytes_per_chunk_limit=32,
              rx_sequence_counts_all_registered_chunks_while_enabled=True,
              parser_and_error_handling_unchanged=True,
              pre_parser_snapshot_avoids_freed_skb_access=True,
              not_a_functional_fix=True, canonical_source_not_modified=True,
              h4_source_sha256=sha((P / 'hci_h4.c').read_bytes()),
              model_illustrative_sync_requires_real_lock_review=True)
(R / 'diagnostic-source-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
