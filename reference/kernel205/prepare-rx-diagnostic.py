from pathlib import Path
import difflib,hashlib,json

here=Path(__file__).resolve().parent;k=Path('/home/cy122/pmos-samurai-kernel136/kernel');out=Path('/mnt/e/edk2-samurai-out/kernel205');path=k/'drivers/bluetooth/hci_qca.c';old=path.read_bytes();sha=lambda b:hashlib.sha256(b).hexdigest()
expected=json.loads((here.parent/'kernel185/source-validation.json').read_text())['source_sha256_after'];assert sha(old)==expected
backup=out/'hci_qca-before-diagnostic-private.c';assert not backup.exists();backup.write_bytes(old);text=old.decode()
def replace(a,b):
 global text
 assert text.count(a)==1,(a,text.count(a));text=text.replace(a,b)
replace('#include <linux/module.h>','#include <linux/module.h>\n#include <linux/timekeeping.h>')
replace('enum qca_rx_phase {','static bool samurai_rx_diag;\nmodule_param(samurai_rx_diag, bool, 0600);\nMODULE_PARM_DESC(samurai_rx_diag, "Private bounded QCA baud-switch RX diagnostics");\n\nenum qca_rx_phase {')
replace('\tu32 requested_baudrate;','''\tu32 requested_baudrate;
\tu32 diag_actual_baudrate;
\tu64 diag_change_start_ns;
\tu64 diag_host_start_ns;
\tu64 diag_host_end_ns;
\tu64 diag_flow_release_ns;''')
anchor='\t\tqca->rx_skb = NULL;\n\t\treturn err;\n'
replace(anchor,'''\t\tif (READ_ONCE(samurai_rx_diag) &&
\t\t    READ_ONCE(qca->rx_phase) == QCA_RX_BAUDRATE_CHANGE) {
\t\t\tunsigned int length = count > 0 ? min_t(int, count, 32) : 0;

\t\t\tbt_dev_err(hu->hdev,
\t\t\t\t   "RXDIAG drop=%u actual=%u change=%llu host_start=%llu host_end=%llu flow_release=%llu",
\t\t\t\t   test_bit(QCA_DROP_VENDOR_EVENT, &qca->flags),
\t\t\t\t   READ_ONCE(qca->diag_actual_baudrate),
\t\t\t\t   READ_ONCE(qca->diag_change_start_ns),
\t\t\t\t   READ_ONCE(qca->diag_host_start_ns),
\t\t\t\t   READ_ONCE(qca->diag_host_end_ns),
\t\t\t\t   READ_ONCE(qca->diag_flow_release_ns));
\t\t\tbt_dev_err(hu->hdev, "RXDIAG head=%*ph", length, buffer);
\t\t}
\t\tqca->rx_skb = NULL;
\t\treturn err;
''')
replace('''\tWRITE_ONCE(qca->requested_baudrate, speed);
\tif (hu->serdev)
\t\tserdev_device_set_baudrate(hu->serdev, speed);
\telse
\t\thci_uart_set_baudrate(hu, speed);''','''\tWRITE_ONCE(qca->requested_baudrate, speed);
\tif (READ_ONCE(samurai_rx_diag))
\t\tWRITE_ONCE(qca->diag_host_start_ns, ktime_get_mono_fast_ns());
\tif (hu->serdev) {
\t\tunsigned int actual = serdev_device_set_baudrate(hu->serdev, speed);

\t\tif (READ_ONCE(samurai_rx_diag))
\t\t\tWRITE_ONCE(qca->diag_actual_baudrate, actual);
\t} else {
\t\thci_uart_set_baudrate(hu, speed);
\t}
\tif (READ_ONCE(samurai_rx_diag))
\t\tWRITE_ONCE(qca->diag_host_end_ns, ktime_get_mono_fast_ns());''')
replace('\t\tWRITE_ONCE(qca->rx_phase, QCA_RX_BAUDRATE_CHANGE);','''\t\tWRITE_ONCE(qca->rx_phase, QCA_RX_BAUDRATE_CHANGE);
\t\tif (READ_ONCE(samurai_rx_diag)) {
\t\t\tWRITE_ONCE(qca->diag_change_start_ns, ktime_get_mono_fast_ns());
\t\t\tWRITE_ONCE(qca->diag_host_start_ns, 0);
\t\t\tWRITE_ONCE(qca->diag_host_end_ns, 0);
\t\t\tWRITE_ONCE(qca->diag_flow_release_ns, 0);
\t\t}''')
# This flow-control release is the one in qca_set_speed, not power-pulse cleanup.
start=text.index('static int qca_set_speed(');end=text.index('static int qca_send_crashbuffer',start);part=text[start:end]
needle='\t\t\thci_uart_set_flow_control(hu, false);';assert part.count(needle)==1
part=part.replace(needle,needle+'\n\t\t\tif (READ_ONCE(samurai_rx_diag))\n\t\t\t\tWRITE_ONCE(qca->diag_flow_release_ns,\n\t\t\t\t\t   ktime_get_mono_fast_ns());');text=text[:start]+part+text[end:]
path.write_text(text);patch=''.join(difflib.unified_diff(old.decode().splitlines(True),text.splitlines(True),fromfile='a/drivers/bluetooth/hci_qca.c',tofile='b/drivers/bluetooth/hci_qca.c'))
(here/'qca-baud-rx-diagnostic.patch').write_text(patch)
r=dict(stage=205,source_before_sha256=expected,source_after_sha256=sha(path.read_bytes()),diagnostics_default_disabled=True,error_bytes_bounded_to_32=True,only_baud_change_error_payloads_logged=True,rx_error_behavior_and_185_pulse_filter_unchanged=True,not_a_functional_fix=True)
(here/'diagnostic-source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
