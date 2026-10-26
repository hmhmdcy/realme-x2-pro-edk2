from pathlib import Path
import difflib, hashlib, json, subprocess

kernel = Path('/home/cy122/x2pro-linux/linux')
out = Path('/mnt/e/edk2-samurai-out/kernel98')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel98')
assert json.loads((out / 'address-isolation-validation.json').read_text())['address_isolation_audit_pass']
relative = 'drivers/bluetooth/hci_qca.c'
path = kernel / relative
assert subprocess.check_output(['git', 'diff', '--', relative], cwd=kernel) == b''
before = path.read_text()
assert not (out / 'hci_qca-before.c').exists()
(out / 'hci_qca-before.c').write_text(before)
text = before
def replace(old, new, count=1):
    global text
    assert text.count(old) == count, old[:60]
    text = text.replace(old, new)
replace('enum qca_capabilities {', '''/* Observation only: parsing, pulse timing and retry behavior are unchanged. */
enum qca_rx_phase {
	QCA_RX_UNSPECIFIED,
	QCA_RX_POWER_OFF_PULSE,
	QCA_RX_POWER_ON_PULSE,
	QCA_RX_PORT_REOPEN,
	QCA_RX_READ_VERSION,
	QCA_RX_BAUDRATE_CHANGE,
	QCA_RX_FIRMWARE_SETUP,
	QCA_RX_READY,
};

enum qca_capabilities {''')
replace('\tstruct sk_buff *rx_skb;\n', '\tstruct sk_buff *rx_skb;\n\tu32 rx_phase;\n\tu32 requested_baudrate;\n')
replace('static int qca_recv(struct hci_uart *hu, const void *data, int count)\n{\n\tstruct qca_data *qca = hu->priv;', 'static int qca_recv(struct hci_uart *hu, const void *data, int count)\n{\n\tstruct qca_data *qca = hu->priv;\n\tunsigned int partial = qca->rx_skb ? qca->rx_skb->len : 0;')
replace('\t\tbt_dev_err(hu->hdev, "Frame reassembly failed (%d)", err);', '''		bt_dev_err(hu->hdev,
			   "Frame reassembly failed (%d) phase=%u baud=%u chunk=%d partial=%u first=%02x",
			   err, READ_ONCE(qca->rx_phase),
			   READ_ONCE(qca->requested_baudrate), count, partial,
			   count > 0 ? ((const u8 *)data)[0] : 0);''')
replace('static inline void host_set_baudrate(struct hci_uart *hu, unsigned int speed)\n{', 'static inline void host_set_baudrate(struct hci_uart *hu, unsigned int speed)\n{\n\tstruct qca_data *qca = hu->priv;\n\n\tWRITE_ONCE(qca->requested_baudrate, speed);')
replace('\tbt_dev_dbg(hu->hdev, "sending power pulse %02x to controller", cmd);', '\tWRITE_ONCE(((struct qca_data *)hu->priv)->rx_phase,\n\t\t   on ? QCA_RX_POWER_ON_PULSE : QCA_RX_POWER_OFF_PULSE);\n\tbt_dev_dbg(hu->hdev, "sending power pulse %02x to controller", cmd);')
replace('\t\tqca_baudrate = qca_get_baudrate_value(speed);\n\t\tbt_dev_dbg', '\t\tWRITE_ONCE(qca->rx_phase, QCA_RX_BAUDRATE_CHANGE);\n\t\tqca_baudrate = qca_get_baudrate_value(speed);\n\t\tbt_dev_dbg')
replace('\treturn qca_port_reopen(hu);', '\tWRITE_ONCE(((struct qca_data *)hu->priv)->rx_phase, QCA_RX_PORT_REOPEN);\n\treturn qca_port_reopen(hu);')
replace('\t\tret = qca_read_soc_version(hdev, &ver, soc_type);', '\t\tWRITE_ONCE(qca->rx_phase, QCA_RX_READ_VERSION);\n\t\tret = qca_read_soc_version(hdev, &ver, soc_type);', 2)
replace('\t/* Setup patch / NVM configurations */\n', '\tWRITE_ONCE(qca->rx_phase, QCA_RX_FIRMWARE_SETUP);\n\t/* Setup patch / NVM configurations */\n')
replace('\thci_devcd_register(hdev, hci_coredump_qca, qca_dmp_hdr, NULL);', '\thci_devcd_register(hdev, hci_coredump_qca, qca_dmp_hdr, NULL);\n\tWRITE_ONCE(qca->rx_phase, QCA_RX_READY);')
path.write_text(text)
patch = ''.join(difflib.unified_diff(before.splitlines(True), text.splitlines(True), fromfile='a/'+relative, tofile='b/'+relative))
(ref / 'qca-rx-error-phase-diagnostics.patch').write_text(patch)
report = dict(diagnostic_only=True, parser_and_retries_unchanged=True,
    qca_source_before_sha256=hashlib.sha256(before.encode()).hexdigest(),
    qca_source_after_sha256=hashlib.sha256(text.encode()).hexdigest())
(out / 'driver-preparation.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report))
