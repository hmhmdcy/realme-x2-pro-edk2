"""Create the isolated candidate from fixed, already cached sources; no build."""
from pathlib import Path
import difflib
import hashlib
import json

R = Path(__file__).resolve().parent
REF = R.parents[1]
COMMIT = 'ba61a62293e0f6bc5838c06f2e85e033e3d702a8'
INPUTS = {
    'hci_serdev.c': (REF / 'bluetooth-static-review-20261023/hci_serdev.c',
        '7ea43973798689b060eb9d7ca4359e87dcd8aa2b49f835cab4d5eb194c10b206'),
    'hci_qca.c': (REF / 'bluetooth-transport-20261023/source/hci_qca.c',
        '645ded4980918a2d0a22dd2d56327bbc69c08e3689e9d313158f0d263e291d90'),
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)


baseline = {}
for name, (path, digest) in INPUTS.items():
    raw = path.read_bytes()
    assert sha(raw) == digest, str(path)
    baseline[name] = raw.decode()
    out = R / 'baseline' / name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(raw)

ser = baseline['hci_serdev.c']
ser = once(ser, '''\tBT_DBG("hdev %p serdev %p", hdev, hu->serdev);

\tif (hu->tx_skb) {''', '''\tBT_DBG("hdev %p serdev %p", hdev, hu->serdev);

\t/* write_work owns tx_skb while running. Keep new wakeups pending
\t * until the flush has finished, as in the line-discipline path.
\t */
\tdisable_work_sync(&hu->write_work);

\tif (hu->tx_skb) {''')
ser = once(ser, '''\tif (test_bit(HCI_UART_PROTO_READY, &hu->flags))
\t\thu->proto->flush(hu);

\treturn 0;''', '''\tpercpu_down_read(&hu->proto_lock);
\tif (test_bit(HCI_UART_PROTO_READY, &hu->flags))
\t\thu->proto->flush(hu);
\tpercpu_up_read(&hu->proto_lock);

\tenable_work(&hu->write_work);
\tclear_bit(HCI_UART_SENDING, &hu->tx_state);
\tif (test_bit(HCI_UART_TX_WAKEUP, &hu->tx_state))
\t\thci_uart_tx_wakeup(hu);

\treturn 0;''')
ser = once(ser, '''\thu->proto->enqueue(hu, skb);

\thci_uart_tx_wakeup(hu);''', '''\tpercpu_down_read(&hu->proto_lock);
\tif (!test_bit(HCI_UART_PROTO_READY, &hu->flags)) {
\t\tpercpu_up_read(&hu->proto_lock);
\t\treturn -EUNATCH;
\t}
\thu->proto->enqueue(hu, skb);
\tpercpu_up_read(&hu->proto_lock);

\thci_uart_tx_wakeup(hu);''')
ser = once(ser, '''\tif (!test_bit(HCI_UART_PROTO_READY, &hu->flags))
\t\treturn 0;

\t/* It does not need a lock here as it is already protected by a mutex in
\t * tty caller
\t */
\thu->proto->recv(hu, data, count);

\tif (hu->hdev)
\t\thu->hdev->stat.byte_rx += count;

\treturn count;''', '''\t/* The tty mutex serializes RX, while proto_lock also excludes close. */
\tpercpu_down_read(&hu->proto_lock);
\tif (!test_bit(HCI_UART_PROTO_READY, &hu->flags)) {
\t\tpercpu_up_read(&hu->proto_lock);
\t\treturn 0;
\t}

\thu->proto->recv(hu, data, count);

\tif (hu->hdev)
\t\thu->hdev->stat.byte_rx += count;
\tpercpu_up_read(&hu->proto_lock);

\treturn count;''')
ser = once(ser, '''\tstruct hci_dev *hdev = hu->hdev;

\tcancel_work_sync(&hu->init_ready);
\tif (test_bit(HCI_UART_REGISTERED, &hu->flags))
\t\thci_unregister_dev(hdev);
\thci_free_dev(hdev);

\tcancel_work_sync(&hu->write_work);

\thu->proto->close(hu);

\tif (test_bit(HCI_UART_PROTO_READY, &hu->flags)) {
\t\tclear_bit(HCI_UART_PROTO_READY, &hu->flags);
\t\tserdev_device_close(hu->serdev);
\t}
\tpercpu_free_rwsem(&hu->proto_lock);''', '''\tstruct hci_dev *hdev;
\tbool close_port;

\t/* Deferred registration failure can already have closed the protocol. */
\tcancel_work_sync(&hu->init_ready);
\thdev = hu->hdev;
\tif (hdev && test_bit(HCI_UART_REGISTERED, &hu->flags))
\t\thci_unregister_dev(hdev);

\t/* Wait for RX/send callbacks and exclude all later TX wakeups before
\t * draining the worker. hdev and protocol data remain alive throughout.
\t */
\tpercpu_down_write(&hu->proto_lock);
\tclose_port = test_and_clear_bit(HCI_UART_PROTO_READY, &hu->flags);
\tclear_bit(HCI_UART_PROTO_INIT, &hu->flags);
\tpercpu_up_write(&hu->proto_lock);
\tdisable_work_sync(&hu->write_work);

\tif (hdev)
\t\thu->proto->close(hu);
\tif (close_port || !hdev)
\t\tserdev_device_close(hu->serdev);

\thu->hdev = NULL;
\tif (hdev)
\t\thci_free_dev(hdev);
\tpercpu_free_rwsem(&hu->proto_lock);''')

# Start with the exact previously validated PM r2, without running its generator.
old_r2 = REF / 'bluetooth-transport-20261023/qca-suspend-recovery-r2.patch'
private_root = Path('/mnt/e/edk2-samurai-out') if Path('/mnt/e').exists() else Path('E:/edk2-samurai-out')
qca_r2 = private_root / 'bluetooth-transport-20261023/hci_qca-pm-r2.c'
raw_r2 = qca_r2.read_bytes()
assert sha(raw_r2) == '74ffff64a7368acc044535dda71535dcdfa31bd0668961c40ada4072b9715339'
qca = raw_r2.decode()
qca = once(qca, '''\t\tif (send_hci_ibs_cmd(HCI_IBS_SLEEP_IND, hu) < 0) {
\t\t\tBT_ERR("Failed to send SLEEP to device");
\t\t\tbreak;
\t\t}''', '''\t\tif (send_hci_ibs_cmd(HCI_IBS_SLEEP_IND, hu) < 0) {
\t\t\tBT_ERR("Failed to send SLEEP to device");
\t\t\tmod_timer(&qca->tx_idle_timer, jiffies +
\t\t\t\t  msecs_to_jiffies(qca->tx_idle_delay));
\t\t\tbreak;
\t\t}''')
qca = once(qca, '''\t\tretransmit = true;
\t\tif (send_hci_ibs_cmd(HCI_IBS_WAKE_IND, hu) < 0) {''', '''\t\tretransmit = true;
\t\t/* Allocation pressure must not strand TX_WAKING without a timer. */
\t\tretrans_delay = msecs_to_jiffies(qca->wake_retrans);
\t\tmod_timer(&qca->wake_retrans_timer, jiffies + retrans_delay);
\t\tif (send_hci_ibs_cmd(HCI_IBS_WAKE_IND, hu) < 0) {''')
qca = once(qca, '''\t\tqca->ibs_sent_wakes++;
\t\tretrans_delay = msecs_to_jiffies(qca->wake_retrans);
\t\tmod_timer(&qca->wake_retrans_timer, jiffies + retrans_delay);
\t\tbreak;''', '''\t\tqca->ibs_sent_wakes++;
\t\tbreak;''')
qca = once(qca, '''\tskb_queue_purge(&qca->tx_wait_q);
\tskb_queue_purge(&qca->txq);
\tskb_queue_purge(&qca->rx_memdump_q);
\t/*''', '''\t/*''')
qca = once(qca, '''\tdestroy_workqueue(qca->workqueue);
\tqca->hu = NULL;''', '''\tdestroy_workqueue(qca->workqueue);
\t/* Drained wake work may have queued a final IBS packet. */
\tskb_queue_purge(&qca->tx_wait_q);
\tskb_queue_purge(&qca->txq);
\tskb_queue_purge(&qca->rx_memdump_q);
\tqca->hu = NULL;''')

candidate = {'hci_serdev.c': ser, 'hci_qca.c': qca}
patch = ''
delta_r2 = ''
for name, text in candidate.items():
    out = R / 'candidate' / name
    out.parent.mkdir(exist_ok=True)
    out.write_bytes(text.encode())
    patch += ''.join(difflib.unified_diff(baseline[name].splitlines(True), text.splitlines(True),
        fromfile='a/drivers/bluetooth/' + name, tofile='b/drivers/bluetooth/' + name))
    previous = raw_r2.decode() if name == 'hci_qca.c' else baseline[name]
    delta_r2 += ''.join(difflib.unified_diff(previous.splitlines(True), text.splitlines(True),
        fromfile='a/drivers/bluetooth/' + name, tofile='b/drivers/bluetooth/' + name))
(R / 'kernel-static-fixes-from-r0.patch').write_bytes(patch.encode())
(R / 'kernel-static-fixes-from-pm-r2.patch').write_bytes(delta_r2.encode())
report = dict(commit=COMMIT, baseline={name: {'path': str(p), 'sha256': digest} for name, (p, digest) in INPUTS.items()},
    previous_pm_r2_sha256=sha(raw_r2), previous_pm_r2_patch_sha256=sha(old_r2.read_bytes()),
    candidate_sha256={name: sha(text.encode()) for name, text in candidate.items()},
    patch_sha256=sha(patch.encode()), delta_from_pm_r2_sha256=sha(delta_r2.encode()),
    old_published_sources_or_artifacts_modified=False, image_or_module_linked=False, device_accessed=False)
(R / 'source-lock.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
