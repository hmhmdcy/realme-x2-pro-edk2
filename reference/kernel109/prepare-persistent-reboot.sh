#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
test "$(cat /etc/samurai-rootfs-stage)" = kernel109
grep -q '^/dev/sda16 / f2fs rw' /proc/mounts
for service in greetd chronyd networkmanager; do
    if rc-service "$service" status >/dev/null 2>&1; then rc-service "$service" stop; fi
done
if pidof wpa_supplicant >/dev/null; then
    for pid in $(pidof wpa_supplicant); do
        test "$(cat /proc/$pid/comm)" = wpa_supplicant
        kill -TERM "$pid"
    done
    sleep 1
fi
test -z "$(pidof wpa_supplicant || true)"
/usr/sbin/samurai-bluetooth stop
echo 18800000.wifi > /sys/bus/platform/drivers/ath10k_snoc/unbind
mpss=$(/usr/sbin/samurai-modem-remoteproc)
echo stop > "$mpss/state"
[ "$(cat "$mpss/state")" = offline ]
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > /var/lib/samurai/k109-before-persistent-reboot-nv.txt
cat /proc/sys/kernel/random/boot_id > /var/lib/samurai/k109-before-persistent-reboot-boot-id.txt
sync
# Close the filesystem before the EUD F1 reset used by the debug flywheel.
mount -o remount,ro /
grep -q '^/dev/sda16 / f2fs ro' /proc/mounts
echo PERSISTENT_ROOTFS_READONLY_CONNECTIVITY_STOPPED
