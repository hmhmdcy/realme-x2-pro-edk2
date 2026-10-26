import host

host.ssh('test -f /var/lib/samurai/k185-load/summary.json && test ! -e /var/lib/samurai/k185-scan-after && test -f /sys/kernel/debug/bluetooth/hci0/ibs/pulse_rx_nuls')
result = host.ssh('nohup python3 /var/lib/samurai/k185-tools/test-bluez-scan-preserve-pairs.py /var/lib/samurai/k185-scan-after > /var/lib/samurai/k185-scan-after-worker-private.log 2>&1 < /dev/null & echo $!')
(host.PRIVATE / 'scan-after-worker-pid-private.txt').write_bytes(result.stdout)
print('Candidate LE/BR-EDR/mixed scan comparison started; existing pairing preserved.')
