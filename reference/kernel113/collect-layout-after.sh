#!/bin/sh
set -eu
umask 077
uname -v | grep -q '^#113 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k113-reboot-radio-clean-3/boot-id-private.txt)"
test "$(cat /proc/sys/kernel/tainted)" = 0
test "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline
test "$(cat /sys/devices/platform/sensor-power/state)" = 'vdd=0 vddio=0'

grep -q '^/dev/sda16 / f2fs rw' /proc/mounts
dest=/var/lib/samurai/k113-layout-after
test ! -e "$dest"
mkdir -m700 "$dest"
for dev in sda sdb sdc sdd sde sdf; do
    sectors=$(blockdev --getsz "/dev/$dev")
    block=$(blockdev --getss "/dev/$dev")
    test "$block" = 4096
    test "$((sectors % 8))" = 0
    blocks=$((sectors / 8))
    blockdev --getsz "/dev/$dev" > "$dest/$dev.geometry"
    blockdev --getss "/dev/$dev" >> "$dest/$dev.geometry"
    cat "/sys/block/$dev/device/model" >> "$dest/$dev.geometry"
    dd if="/dev/$dev" of="$dest/$dev.head" bs=4096 count=34 status=none
    dd if="/dev/$dev" of="$dest/$dev.tail" bs=4096 skip=$((blocks - 34)) count=34 status=none
done
sha256sum /dev/sde11 /dev/sde32 /dev/sda2 > "$dest/partition-check.sha256"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-check.txt"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state.txt"
dmesg > "$dest/dmesg.txt"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -cf /tmp/k113-layout-after.tar .
sha256sum /tmp/k113-layout-after.tar
echo LAYOUT_AFTER_CAPTURED_READ_ONLY
