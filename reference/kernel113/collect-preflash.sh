#!/bin/sh
set -eu
umask 077
uname -v | grep -q '^#112 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k112-reboot-radio-clean-2/boot-id-private.txt)"
test "$(cat /proc/sys/kernel/tainted)" = 0
test "$(cat /sys/class/remoteproc/remoteproc0/name)" = slpi
test "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline
test -z "$(pidof hexagonrpcd)"
grep -q '^/dev/sda16 / f2fs rw' /proc/mounts
dest=/var/lib/samurai/k113-preflash
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
cat /proc/mounts > "$dest/mounts.txt"
uname -a > "$dest/uname.txt"
cat /sys/firmware/fdt > "$dest/live-fdt-private.dtb"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -cf /tmp/k113-preflash.tar .
sha256sum /tmp/k113-preflash.tar
echo KERNEL113_PREFLASH_READONLY_CAPTURED
