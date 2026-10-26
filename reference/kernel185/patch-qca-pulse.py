"""Separate the WCN399x UART power-pulse NUL prefix from the H4 data path."""
from pathlib import Path
import difflib
import hashlib
import json
import subprocess

k = Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/kernel185')
out.mkdir(exist_ok=True)
file = k / 'drivers/bluetooth/hci_qca.c'
before = file.read_text()
assert 'QCA_POWER_PULSE' not in before
(out / 'hci_qca-before-private.c').write_text(before)
baseline = json.loads((ref.parent / 'kernel183/source-validation.json').read_text())['source_sha256']
for name, digest in baseline.items():
    assert hashlib.sha256((k / name).read_bytes()).hexdigest() == digest
after = before.replace('\tQCA_DEBUGFS_CREATED,\n', '\tQCA_DEBUGFS_CREATED,\n\tQCA_POWER_PULSE,\n')
after = after.replace('/* Observation only: parsing, pulse timing and retry behavior are unchanged. */',
                      '/* Diagnostic tags are independent of the power-pulse receive window. */')
after = after.replace('\tu32 requested_baudrate;\n', '\tu32 requested_baudrate;\n\tatomic_t pulse_rx_nuls;\n')
after = after.replace('\thu->priv = qca;\n', '\tatomic_set(&qca->pulse_rx_nuls, 0);\n\thu->priv = qca;\n')
assert after.count('atomic_set(&qca->pulse_rx_nuls, 0);') == 1
after = after.replace('\tmode = 0444;\n', '\tmode = 0444;\n\tdebugfs_create_atomic_t("pulse_rx_nuls", mode, ibs_dir,\n\t\t\t\t&qca->pulse_rx_nuls);\n')
old = '''\tstruct qca_data *qca = hu->priv;
\tunsigned int partial = qca->rx_skb ? qca->rx_skb->len : 0;

\tif (!test_bit(HCI_UART_REGISTERED, &hu->flags))
\t\treturn -EUNATCH;

\tqca->rx_skb = h4_recv_buf(hu, qca->rx_skb, data, count,
'''
new = '''\tstruct qca_data *qca = hu->priv;
\tunsigned int partial = qca->rx_skb ? qca->rx_skb->len : 0;
\tconst u8 *buffer = data;
\tint received = count;
\tint nuls = 0;

\tif (!test_bit(HCI_UART_REGISTERED, &hu->flags))
\t\treturn -EUNATCH;

\t/* Power-pulse traffic is not H4. Preserve zeros in partial frames. */
\tif (test_bit(QCA_POWER_PULSE, &qca->flags) && !qca->rx_skb) {
\t\twhile (count > 0 && *buffer == 0) {
\t\t\tbuffer++;
\t\t\tcount--;
\t\t\tnuls++;
\t\t}
\t\tatomic_add(nuls, &qca->pulse_rx_nuls);
\t\tif (!count)
\t\t\treturn received;
\t}

\tqca->rx_skb = h4_recv_buf(hu, qca->rx_skb, buffer, count,
'''
assert after.count(old) == 1
after = after.replace(old, new)
after = after.replace('count > 0 ? ((const u8 *)data)[0] : 0);', 'count > 0 ? buffer[0] : 0);')
start = after.index('static int qca_recv(struct hci_uart *hu,')
end = after.index('\nstatic struct sk_buff *qca_dequeue', start)
part = after[start:end]
assert part.count('\treturn count;') == 1
after = after[:start] + part.replace('\treturn count;', '\treturn received;') + after[end:]
start = after.index('static int qca_send_power_pulse(')
end = after.index('\nstatic unsigned int qca_get_speed', start)
part = after[start:end]
part = part.replace('\tint ret;\n', '\tstruct qca_data *qca = hu->priv;\n\tint ret;\n')
part = part.replace('\tserdev_device_write_flush(hu->serdev);', '\tset_bit(QCA_POWER_PULSE, &qca->flags);\n\tserdev_device_write_flush(hu->serdev);')
part = part.replace('''\tif (ret < 0) {
\t\tbt_dev_err(hu->hdev, "failed to send power pulse %02x", cmd);
\t\treturn ret;
\t}''', '''\tif (ret != sizeof(cmd)) {
\t\tbt_dev_err(hu->hdev, "failed to send power pulse %02x", cmd);
\t\tif (ret >= 0)
\t\t\tret = -EIO;
\t\tgoto restore_flow;
\t}''')
part = part.replace('''\treturn 0;
}''', '''\tclear_bit(QCA_POWER_PULSE, &qca->flags);
\treturn 0;

restore_flow:
\thci_uart_set_flow_control(hu, false);
\tclear_bit(QCA_POWER_PULSE, &qca->flags);
\treturn ret;
}''')
after = after[:start] + part + after[end:]
assert after.count('set_bit(QCA_POWER_PULSE') == 1
assert after.count('clear_bit(QCA_POWER_PULSE') == 2
patch = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                  fromfile='a/drivers/bluetooth/hci_qca.c', tofile='b/drivers/bluetooth/hci_qca.c'))
file.write_text(after)
(ref / 'qca-power-pulse-rx.patch').write_text(patch)
subprocess.run(['git', 'diff', '--check'], cwd=k, check=True)
check = subprocess.run(['perl', 'scripts/checkpatch.pl', '--no-signoff', '--strict', str(ref / 'qca-power-pulse-rx.patch')],
                       cwd=k, capture_output=True)
(out / 'checkpatch-private.log').write_bytes(check.stdout + check.stderr)
report = {'source_sha256_before': hashlib.sha256(before.encode()).hexdigest(),
          'source_sha256_after': hashlib.sha256(after.encode()).hexdigest(),
          'other183_sources_verified': True, 'checkpatch_exit': check.returncode,
          'pulse_timings_unchanged': True, 'h4_errors_outside_window_preserved': True,
          'read_only_counter_added': True, 'short_write_and_flow_cleanup_fixed': True,
          'runtime_tested': False}
(ref / 'source-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
assert check.returncode == 0
