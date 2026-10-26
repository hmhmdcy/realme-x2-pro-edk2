#!/bin/sh
set -eu
[ "$(cat /proc/sys/kernel/random/boot_id)" = dfe8e722-f6b7-4ce8-85cc-17dfba80f69d ]
[ ! -e /tmp/k91-meta-rmtfs.txt ]
echo 'd3a19b2f2daa1c85345182095510ee6d2e5db065118855c8938d9ad7d82dff4e  /tmp/k91-tqftpserv-ram-probe2' | sha256sum -c -
sha256sum -c /tmp/k91-nv-source-hashes.txt > /tmp/k91-meta-nv-before.txt
(cd /tmp/k91-nv && sha256sum -c /tmp/k91-nv-SHA256SUMS) > /tmp/k91-meta-nv-files.txt
echo stop > /sys/class/remoteproc/remoteproc0/state
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline ]
echo 18800000.wifi > /sys/bus/platform/drivers/ath10k_snoc/unbind
echo 18800000.wifi > /sys/bus/platform/drivers/ath10k_snoc/bind
kill "$(cat /tmp/k91-tqftpserv.pid)" "$(cat /tmp/k91-rmtfs-cow.pid)"
sleep 1
/tmp/k91-qrtr-lookup > /tmp/k91-meta-qrtr-offline.txt
! grep -qE '^ *14 |^ *4096 ' /tmp/k91-meta-qrtr-offline.txt
SAMURAI_TFTP_FIRMWARE_ROOT=/tmp/k91-firmware/qcom/sm8150/realme/samurai /tmp/k91-tqftpserv-ram-probe2 -d > /tmp/k91-meta-tftp.txt 2>&1 &
echo $! > /tmp/k91-tqftpserv.pid
/tmp/k91-rmtfs-cow > /tmp/k91-meta-rmtfs.txt 2>&1 &
echo $! > /tmp/k91-rmtfs-cow.pid
sleep 1
kill -0 "$(cat /tmp/k91-tqftpserv.pid)" "$(cat /tmp/k91-rmtfs-cow.pid)"
grep -q 'RMTFS RAM COW ready' /tmp/k91-meta-rmtfs.txt
/tmp/k91-qrtr-lookup > /tmp/k91-meta-qrtr-before.txt
grep -qE '^ *14 ' /tmp/k91-meta-qrtr-before.txt
grep -qE '^ *4096 ' /tmp/k91-meta-qrtr-before.txt
echo start > /sys/class/remoteproc/remoteproc0/state
sleep 5
/tmp/k91-qrtr-lookup > /tmp/k91-meta-qrtr-after.txt
cat /proc/uptime
cat /sys/class/remoteproc/remoteproc0/state
cat /proc/sys/kernel/tainted
ls /sys/class/net
head -50 /tmp/k91-meta-tftp.txt
head -30 /tmp/k91-meta-rmtfs.txt
dmesg > /tmp/k91-meta-start-dmesg.txt
sha256sum /tmp/k91-meta-start-dmesg.txt
