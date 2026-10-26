#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = running ]
test -e /sys/bus/platform/drivers/ath10k_snoc/18800000.wifi
if test -e /sys/class/net/wlan0; then
    /usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 terminate | grep -qx OK
    sleep 1
fi
/usr/sbin/samurai-bluetooth stop
echo 18800000.wifi > /sys/bus/platform/drivers/ath10k_snoc/unbind
echo WLAN_UNBOUND
echo stop > /sys/class/remoteproc/remoteproc0/state
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline ]
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt
cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted
echo CONNECTIVITY_STOPPED
