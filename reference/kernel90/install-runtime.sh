#!/bin/sh
set -eu
[ "$(cat /proc/sys/kernel/random/boot_id)" = 9141a405-6968-4af3-97d2-e166b957030b ]
uname -a | grep -q '#89 SMP PREEMPT'
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline ]
[ "$(cat /sys/class/remoteproc/remoteproc0/firmware)" = qcom/sm8150/realme/samurai/modem.mdt ]
[ ! -e /tmp/k90-firmware ]
echo 'd4d513332310b5db72b314c78b9a91cad539c6855f12608107dda0e4ca0e16e3  /tmp/k90-runtime-firmware.tar' | sha256sum -c -
echo '11f5a225470b536b5dd0a9e181059447b696f4e89c2884ee28e5d6d48bb32074  /tmp/k90-qrtr-lookup' | sha256sum -c -
echo '274fd4fd849fb9e49853eefd7923f86a7554af9ecf664a324ae72b498f19ec18  /tmp/k90-tqftpserv-ro' | sha256sum -c -
mkdir /tmp/k90-firmware
tar -xf /tmp/k90-runtime-firmware.tar -C /tmp/k90-firmware
cd /tmp/k90-firmware
sha256sum -c /tmp/k90-runtime-firmware-sha256.txt > /tmp/k90-runtime-firmware-check.txt
chmod 755 /tmp/k90-qrtr-lookup /tmp/k90-tqftpserv-ro
echo /tmp/k90-firmware > /sys/module/firmware_class/parameters/path
SAMURAI_TFTP_FIRMWARE_ROOT=/tmp/k90-firmware/qcom/sm8150/realme/samurai /tmp/k90-tqftpserv-ro -d > /tmp/k90-tqftpserv.txt 2>&1 &
pid=$!
echo "$pid" >/tmp/k90-tqftpserv.pid
sleep 1
kill -0 "$pid"
/tmp/k90-qrtr-lookup > /tmp/k90-qrtr-before-start.txt
cat /tmp/k90-qrtr-before-start.txt
cat /tmp/k90-tqftpserv.txt

