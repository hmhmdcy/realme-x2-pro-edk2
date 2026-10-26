#!/bin/sh
# Explicit PAS start of reviewed, same-handset firmware; no NV storage service.
set -eu
[ "$(cat /proc/sys/kernel/random/boot_id)" = f3c087f8-e9d3-491f-b5ad-c5511082fe29 ]
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline ]
[ "$(cat /sys/class/remoteproc/remoteproc0/firmware)" = qcom/sm8150/realme/samurai/modem.mdt ]
[ "$(cat /sys/module/firmware_class/parameters/path)" = /tmp/k89-firmware ]
kill -0 "$(cat /tmp/k89-tqftpserv.pid)"
[ ! -e /tmp/k89-mpss-start.txt ]
dmesg > /tmp/k89-before-mpss-dmesg.txt
sha256sum /tmp/k89-before-mpss-dmesg.txt
set +e
echo start > /sys/class/remoteproc/remoteproc0/state 2>/tmp/k89-mpss-start-error.txt
rc=$?
set -e
{
 echo "start_exit=$rc"
 cat /proc/sys/kernel/random/boot_id
 cat /proc/uptime
 cat /proc/sys/kernel/tainted
 cat /sys/class/remoteproc/remoteproc0/state
} > /tmp/k89-mpss-start.txt
cat /tmp/k89-mpss-start.txt
cat /tmp/k89-mpss-start-error.txt
sleep 2
/tmp/k89-qrtr-lookup > /tmp/k89-qrtr-after-start.txt
cat /tmp/k89-qrtr-after-start.txt
dmesg > /tmp/k89-after-mpss-dmesg.txt
sha256sum /tmp/k89-after-mpss-dmesg.txt
tail -30 /tmp/k89-after-mpss-dmesg.txt
