#!/bin/sh
set -eu
umask 077
test "$#" = 1
test "$(cat /proc/sys/kernel/random/boot_id)" = "$1"
test "$(cat /var/lib/samurai/k200-baseline/boot-id-private.txt)" = "$1"
test ! -e /var/lib/samurai/k200-reboot-tools/transition-started-private
echo STARTED > /var/lib/samurai/k200-reboot-tools/transition-started-private
test ! -e /sys/module/qcom_camss
test -f /var/lib/samurai/k200-preliminary/summary-private.json
if rc-service networkmanager status >/dev/null 2>&1; then timeout -s TERM -k 2 25 rc-service networkmanager stop; fi
for pid in $(pidof wpa_supplicant || true); do test "$(cat /proc/$pid/comm)" = wpa_supplicant;kill -TERM "$pid";done
sleep 1
test -z "$(pidof wpa_supplicant || true)"
test "$(readlink -f /sys/bus/platform/devices/18800000.wifi/driver)" = /sys/bus/platform/drivers/ath10k_snoc
echo 18800000.wifi > /sys/bus/platform/drivers/ath10k_snoc/unbind
test ! -e /sys/bus/platform/devices/18800000.wifi/driver
test ! -e /sys/class/net/wlan0
sh /var/lib/samurai/k200-reboot-tools/finish-quiesce-after-network-stop.sh
sh /tmp/k200-freeze-for-bootloader.sh "$1"
python3 /var/lib/samurai/k200-reboot-tools/linux-restart2-bootloader.py --inspect
exec python3 /var/lib/samurai/k200-reboot-tools/linux-restart2-bootloader.py
