#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#101 SMP PREEMPT'
[ "$(cat /sys/class/block/sde/device/model)" = 'KLUDG4UHDB-B2D1 ' ]
grep -qx PARTNAME=boot /sys/class/block/sde11/uevent
grep -qx PARTNAME=logdump /sys/class/block/sde32/uevent
[ "$(cat /sys/class/block/sde11/size)" = 196608 ]
[ "$(cat /sys/class/block/sde32/size)" = 131072 ]
dir=/tmp/k103-preflash
test ! -e "$dir"
mkdir -m700 "$dir"
mountpoint -q /sys/kernel/debug || mount -t debugfs debugfs /sys/kernel/debug
dmesg > "$dir/dmesg.txt"
{
    uname -a
    cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted
    for p in /sys/class/remoteproc/remoteproc*; do cat "$p/name" "$p/state"; done
    ls /sys/class/drm /sys/class/graphics
    cat /sys/kernel/debug/dri/1/encoder-0/status
} > "$dir/state.txt"
cat "$(/tmp/k103-haptics-device)/status" > "$dir/haptics-status.txt"
cat /proc/modules > "$dir/modules.txt"
ps > "$dir/processes.txt"
cp /run/samurai-wifi-boot.log /run/samurai-bluetooth-boot.log "$dir/"
cp -a /run/samurai-radio-address "$dir/"
cp /run/samurai-wifi/nv-source-hashes.txt "$dir/"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-source-check.txt"
sha256sum /dev/sda2 > "$dir/persist-before.sha"
dd if=/dev/sde11 of=/tmp/k103-boot-partition-before.img bs=1048576
dd if=/dev/sde32 of=/tmp/k103-logdump-before.img bs=1048576
{
    cat /proc/sys/kernel/random/boot_id
    head -c 6682624 /dev/sde11 | sha256sum
    sha256sum /dev/sde11 /dev/sde32 /tmp/k103-boot-partition-before.img /tmp/k103-logdump-before.img
} > "$dir/guard.txt"
grep -q '^94fcd45f23179c3ce1bae258e40b2d0fc8e072d8a257aa78a31c59d4e83cc4ff ' "$dir/guard.txt"
grep -q '^6c96d1de3a12c64e321450b686d0ed62fb75e34b203e2bded5e972246f40f75d ' "$dir/guard.txt"
[ "$(cat /proc/sys/kernel/tainted)" = 0 ]
(cd "$dir" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k103-preflash.tar k103-preflash
sha256sum /tmp/k103-preflash.tar /tmp/k103-boot-partition-before.img /tmp/k103-logdump-before.img
echo PREFLASH_COMPLETE
