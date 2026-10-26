#!/bin/sh
set -eu
umask 077
[ "$#" = 2 ]
prefix=$1
case "$prefix" in *[!a-z0-9-]*|'') exit 2;; esac
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$2" ]
test "$(cat /etc/samurai-rootfs-stage)" = kernel109
dir=/var/lib/samurai/k109-normal-reboot-$prefix
test ! -e "$dir"
mkdir "$dir"
cat /proc/sys/kernel/random/boot_id /proc/uptime > "$dir/before-state.txt"
for service in greetd chronyd networkmanager; do
    if rc-service "$service" status >/dev/null 2>&1; then rc-service "$service" stop; fi
done
for pid in $(pidof wpa_supplicant || true); do
    test "$(cat /proc/$pid/comm)" = wpa_supplicant
    kill -TERM "$pid"
done
sleep 1
test -z "$(pidof wpa_supplicant || true)"
/usr/sbin/samurai-bluetooth stop
echo 18800000.wifi > /sys/bus/platform/drivers/ath10k_snoc/unbind
mpss=$(/usr/sbin/samurai-modem-remoteproc)
echo stop > "$mpss/state"
[ "$(cat "$mpss/state")" = offline ]
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-check.txt"
sync
# OpenRC stops remaining services and unmounts filesystems before resetting.
nohup /bin/sh -c 'sleep 2; exec /sbin/reboot' > /run/k109-normal-reboot.log 2>&1 < /dev/null &
echo NORMAL_OPENRC_PERSISTENT_REBOOT_REQUESTED
