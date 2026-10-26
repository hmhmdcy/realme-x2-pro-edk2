#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#99 SMP PREEMPT'
[ "$(cat /sys/class/block/sde/device/model)" = 'KLUDG4UHDB-B2D1 ' ]
grep -qx PARTNAME=boot /sys/class/block/sde11/uevent
grep -qx PARTNAME=logdump /sys/class/block/sde32/uevent
[ "$(cat /sys/class/block/sde11/size)" = 196608 ]
[ "$(cat /sys/class/block/sde32/size)" = 131072 ]
dir=/tmp/k101-preflash
test ! -e "$dir"
mkdir -m700 "$dir"
mountpoint -q /sys/kernel/debug || mount -t debugfs debugfs /sys/kernel/debug
dmesg > "$dir/dmesg.txt"
{
    uname -a
    cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted
    cat /sys/class/remoteproc/remoteproc0/state
    ls /sys/class/drm /sys/class/graphics
    cat /sys/kernel/debug/dri/1/encoder-0/status
} > "$dir/state.txt"
cat /sys/bus/i2c/devices/1-005a/status > "$dir/haptics-status.txt"
cat /proc/modules > "$dir/modules.txt"
ps > "$dir/processes.txt"
cp /run/samurai-wifi-boot.log /run/samurai-bluetooth-boot.log "$dir/"
cp -a /run/samurai-radio-address "$dir/"
cp /run/samurai-wifi/nv-source-hashes.txt "$dir/"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-source-check.txt"
sha256sum /dev/sda2 > "$dir/persist-before.sha"
dd if=/dev/sde11 of=/tmp/k101-boot-partition-before.img bs=1048576
dd if=/dev/sde32 of=/tmp/k101-logdump-before.img bs=1048576
{
    cat /proc/sys/kernel/random/boot_id
    head -c 6680576 /dev/sde11 | sha256sum
    sha256sum /dev/sde11 /dev/sde32 /tmp/k101-boot-partition-before.img /tmp/k101-logdump-before.img
} > "$dir/guard.txt"
grep -q '^7fa3a6879f8e3409fff129befedc32c6e67785fac18665984f52bf2d0f067c1f ' "$dir/guard.txt"
grep -q '^02554a24fa661c00f2684f8cc1aee3ae57b5887c552bb335d372e8276fbdb9ea ' "$dir/guard.txt"
[ "$(cat /proc/sys/kernel/tainted)" = 0 ]
(cd "$dir" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k101-preflash.tar k101-preflash
sha256sum /tmp/k101-preflash.tar /tmp/k101-boot-partition-before.img /tmp/k101-logdump-before.img
echo PREFLASH_COMPLETE
