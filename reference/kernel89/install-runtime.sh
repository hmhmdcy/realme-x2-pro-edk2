#!/bin/sh
set -eu
[ "$(cat /proc/sys/kernel/random/boot_id)" = f3c087f8-e9d3-491f-b5ad-c5511082fe29 ]
uname -a | grep -q '#89 SMP PREEMPT'
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline ]
[ "$(cat /sys/class/remoteproc/remoteproc0/firmware)" = qcom/sm8150/realme/samurai/modem.mdt ]
[ ! -e /tmp/k89-firmware ]
echo 'd4d513332310b5db72b314c78b9a91cad539c6855f12608107dda0e4ca0e16e3  /tmp/k89-runtime-firmware.tar' | sha256sum -c -
echo '11f5a225470b536b5dd0a9e181059447b696f4e89c2884ee28e5d6d48bb32074  /tmp/k89-qrtr-lookup' | sha256sum -c -
echo '274fd4fd849fb9e49853eefd7923f86a7554af9ecf664a324ae72b498f19ec18  /tmp/k89-tqftpserv-ro' | sha256sum -c -
mkdir /tmp/k89-firmware
tar -xf /tmp/k89-runtime-firmware.tar -C /tmp/k89-firmware
cd /tmp/k89-firmware
sha256sum -c /tmp/k89-runtime-firmware-sha256.txt > /tmp/k89-runtime-firmware-check.txt
chmod 755 /tmp/k89-qrtr-lookup /tmp/k89-tqftpserv-ro
echo /tmp/k89-firmware > /sys/module/firmware_class/parameters/path
SAMURAI_TFTP_FIRMWARE_ROOT=/tmp/k89-firmware/qcom/sm8150/realme/samurai /tmp/k89-tqftpserv-ro -d > /tmp/k89-tqftpserv.txt 2>&1 &
pid=$!
echo "$pid" >/tmp/k89-tqftpserv.pid
sleep 1
kill -0 "$pid"
/tmp/k89-qrtr-lookup > /tmp/k89-qrtr-before-start.txt
cat /tmp/k89-qrtr-before-start.txt
cat /tmp/k89-tqftpserv.txt
