#!/bin/sh
set -eu
umask 077
[ "$(cat /proc/sys/kernel/random/boot_id)" = dfe8e722-f6b7-4ce8-85cc-17dfba80f69d ]
test ! -e /run/samurai-wifi/nv
echo '8a9e9bb15daa5fe2763f4c616cd936d791d208f403cc734dd7c8efc2479cf89b  /tmp/k92-runtime-tools.tar' | sha256sum -c -
tar -xf /tmp/k92-runtime-tools.tar -C /
/tmp/k91-wpa_cli -p/tmp/k91-wpa-ctrl -iwlan0 terminate
sleep 1
echo stop > /sys/class/remoteproc/remoteproc0/state
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline ]
echo 18800000.wifi > /sys/bus/platform/drivers/ath10k_snoc/unbind
echo 18800000.wifi > /sys/bus/platform/drivers/ath10k_snoc/bind
for file in /tmp/k91-tqftpserv.pid /tmp/k91-rmtfs-cow.pid; do
    pid=$(cat "$file")
    case "$pid" in ''|*[!0-9]*) exit 1;; esac
    tr '\0' ' ' < "/proc/$pid/cmdline" | grep -qE '^/tmp/k91-(rmtfs-cow|tqftpserv-ram-probe2)'
    kill "$pid"
done
sleep 1
/usr/sbin/qrtr-lookup > /tmp/k92-qrtr-offline.txt
! grep -qE '^ *14 |^ *4096 ' /tmp/k92-qrtr-offline.txt
nohup /usr/sbin/samurai-wifi start > /run/samurai-wifi-pretest.log 2>&1 < /dev/null &
echo $! > /tmp/k92-pretest.pid
sleep 3
cat /run/samurai-wifi-pretest.log
cat /proc/uptime /proc/sys/kernel/tainted /sys/class/remoteproc/remoteproc0/state
