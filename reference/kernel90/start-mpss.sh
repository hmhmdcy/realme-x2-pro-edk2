#!/bin/sh
# Explicit PAS start of reviewed, same-handset firmware; no NV storage service.
set -eu
[ "$(cat /proc/sys/kernel/random/boot_id)" = 9141a405-6968-4af3-97d2-e166b957030b ]
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline ]
[ "$(cat /sys/class/remoteproc/remoteproc0/firmware)" = qcom/sm8150/realme/samurai/modem.mdt ]
[ "$(cat /sys/module/firmware_class/parameters/path)" = /tmp/k90-firmware ]
kill -0 "$(cat /tmp/k90-tqftpserv.pid)"
[ ! -e /tmp/k90-mpss-start.txt ]
dmesg > /tmp/k90-before-mpss-dmesg.txt
sha256sum /tmp/k90-before-mpss-dmesg.txt
set +e
echo start > /sys/class/remoteproc/remoteproc0/state 2>/tmp/k90-mpss-start-error.txt
rc=$?
set -e
{
 echo "start_exit=$rc"
 cat /proc/sys/kernel/random/boot_id
 cat /proc/uptime
 cat /proc/sys/kernel/tainted
 cat /sys/class/remoteproc/remoteproc0/state
} > /tmp/k90-mpss-start.txt
cat /tmp/k90-mpss-start.txt
cat /tmp/k90-mpss-start-error.txt
sleep 2
/tmp/k90-qrtr-lookup > /tmp/k90-qrtr-after-start.txt
cat /tmp/k90-qrtr-after-start.txt
dmesg > /tmp/k90-after-mpss-dmesg.txt
sha256sum /tmp/k90-after-mpss-dmesg.txt
tail -30 /tmp/k90-after-mpss-dmesg.txt

