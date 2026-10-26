#!/bin/sh
set -eu
umask 077
[ "$(cat /proc/sys/kernel/random/boot_id)" = 7198e2c9-17e4-42af-ac12-71a2013b5ea8 ]
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = running ]
test -e /sys/bus/platform/drivers/ath10k_snoc/18800000.wifi
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 terminate
sleep 1
/tmp/bt-mgmt-probe4 off
# Detach the WLAN client while the remote firmware is still responding.
echo 18800000.wifi > /sys/bus/platform/drivers/ath10k_snoc/unbind
echo WLAN_UNBOUND
echo stop > /sys/class/remoteproc/remoteproc0/state
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline ]
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt
cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted
echo CONNECTIVITY_STOPPED
