#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#109 SMP PREEMPT'
test -d /var/lib/samurai/k111-preflash
test ! -e /var/lib/samurai/k111-bootloader-quiesce
dir=/var/lib/samurai/k111-bootloader-quiesce
mkdir -m700 "$dir"
cat /proc/sys/kernel/random/boot_id > "$dir/boot-id-private.txt"
for service in greetd chronyd networkmanager iio-sensor-proxy; do
    if rc-service "$service" status >/dev/null 2>&1; then rc-service "$service" stop; fi
done
# Drain the stopped desktop's lingering per-user daemons before freezing F2FS.
for pid in $(pgrep -u 10000 || true); do kill -TERM "$pid" 2>/dev/null || true; done
sleep 2
for pid in $(pgrep -u 10000 || true); do kill -KILL "$pid" 2>/dev/null || true; done
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
dmesg > "$dir/dmesg.txt"
sync
test "$(cat /proc/sys/kernel/tainted)" = 0
grep -q ' /run tmpfs rw' /proc/mounts
echo QUIESCED > /run/k111-bootloader-state
fsfreeze -f /
echo FROZEN > /run/k111-bootloader-state
# This marker is emitted after the kernel reports a successfully frozen root.
echo KERNEL111_F2FS_FROZEN_FOR_BOOTLOADER
