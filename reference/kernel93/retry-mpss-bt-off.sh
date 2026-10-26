#!/bin/sh
set -eu
umask 077
[ "$(cat /proc/sys/kernel/random/boot_id)" = b65a234f-44f4-4ad3-9d40-ecafdeb233b1 ]
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = crashed ]
test ! -e /sys/class/net/wlan0
# Do not race an earlier start loop.
if [ -d /proc/134 ]; then
    grep -q samurai-wifi /proc/134/cmdline
    kill 134
fi
/tmp/k93-bt-mgmt-probe off
echo 18800000.wifi > /sys/bus/platform/drivers/ath10k_snoc/unbind
echo stop > /sys/class/remoteproc/remoteproc0/state
echo 18800000.wifi > /sys/bus/platform/drivers/ath10k_snoc/bind
echo start > /sys/class/remoteproc/remoteproc0/state
for attempt in $(seq 1 60); do
    test -e /sys/class/net/wlan0 && break
    sleep 1
done
test -e /sys/class/net/wlan0
ip link set wlan0 up
nohup /usr/sbin/wpa_supplicant -Dnl80211 -iwlan0 -c/run/samurai-wifi/wpa.conf > /run/samurai-wifi/wpa-retry.log 2>&1 < /dev/null &
echo $! > /run/samurai-wifi/wpa.pid
sleep 45
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = running ]
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt
echo WIFI_RETRY_READY
