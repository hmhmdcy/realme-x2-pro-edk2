#!/bin/sh
set -eu
[ "$(cat /proc/sys/kernel/random/boot_id)" = dfe8e722-f6b7-4ce8-85cc-17dfba80f69d ]
[ ! -e /tmp/k91-stability2-rmtfs.txt ]
echo 'd3a19b2f2daa1c85345182095510ee6d2e5db065118855c8938d9ad7d82dff4e  /tmp/k91-tqftpserv-ram-probe2' | sha256sum -c -
echo '38b4d930f50fc02193388cdc4d8fa1146ea6a53f515d3185696551d293ade846  /tmp/k91-rmtfs-cow' | sha256sum -c -
sha256sum -c /tmp/k91-nv-source-hashes.txt > /tmp/k91-stability2-nv-before.txt
(cd /tmp/k91-nv && sha256sum -c /tmp/k91-nv-SHA256SUMS) > /tmp/k91-stability2-nv-files.txt
trace=/sys/kernel/tracing/instances/k91qrtr2
mkdir "$trace"
echo 512 > "$trace/buffer_size_kb"
echo 1 > "$trace/events/qrtr/enable"
echo 1 > "$trace/tracing_on"
if [ -e /tmp/k91-wpa.pid ]; then
    /tmp/k91-wpa_cli -p/tmp/k91-wpa-ctrl -iwlan0 terminate
    sleep 1
    test ! -e /tmp/k91-wpa.pid
fi
echo stop > /sys/class/remoteproc/remoteproc0/state
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline ]
echo 18800000.wifi > /sys/bus/platform/drivers/ath10k_snoc/unbind
echo 18800000.wifi > /sys/bus/platform/drivers/ath10k_snoc/bind
kill "$(cat /tmp/k91-tqftpserv.pid)" "$(cat /tmp/k91-rmtfs-cow.pid)"
sleep 1
/tmp/k91-qrtr-lookup > /tmp/k91-stability2-qrtr-offline.txt
! grep -qE '^ *14 |^ *4096 ' /tmp/k91-stability2-qrtr-offline.txt
SAMURAI_TFTP_FIRMWARE_ROOT=/tmp/k91-firmware/qcom/sm8150/realme/samurai /tmp/k91-tqftpserv-ram-probe2 -d > /tmp/k91-stability2-tftp.txt 2>&1 &
echo $! > /tmp/k91-tqftpserv.pid
/tmp/k91-rmtfs-cow > /tmp/k91-stability2-rmtfs.txt 2>&1 &
echo $! > /tmp/k91-rmtfs-cow.pid
sleep 1
kill -0 "$(cat /tmp/k91-tqftpserv.pid)" "$(cat /tmp/k91-rmtfs-cow.pid)"
grep -q 'RMTFS RAM COW ready' /tmp/k91-stability2-rmtfs.txt
/tmp/k91-qrtr-lookup > /tmp/k91-stability2-qrtr-before.txt
grep -qE '^ *14 ' /tmp/k91-stability2-qrtr-before.txt
grep -qE '^ *4096 ' /tmp/k91-stability2-qrtr-before.txt
echo start > /sys/class/remoteproc/remoteproc0/state
sleep 5
/tmp/k91-qrtr-lookup > /tmp/k91-stability2-qrtr-after5.txt
cat /proc/uptime /proc/sys/kernel/tainted
cat /sys/class/remoteproc/remoteproc0/state
ls /sys/class/net
grep -c '^\[RMTFS\] open ' /tmp/k91-stability2-rmtfs.txt || true
grep -c 'read request for' /tmp/k91-stability2-tftp.txt || true
cat "$trace/trace" > /tmp/k91-stability2-qrtr-trace5.txt
dmesg > /tmp/k91-stability2-dmesg5.txt
sha256sum /tmp/k91-stability2-qrtr-trace5.txt /tmp/k91-stability2-dmesg5.txt
