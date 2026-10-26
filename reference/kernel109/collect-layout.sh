#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ] || [ "$#" = 2 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
prefix=${2:-before}
case "$prefix" in *[!a-z0-9-]*|'') exit 2;; esac
dir=/tmp/k109-layout-$prefix
test ! -e "$dir"
mkdir -m700 "$dir"
for disk in sda sdb sdc sdd sde sdf; do
    [ "$(cat /sys/class/block/$disk/queue/logical_block_size)" = 4096 ]
    size=$(cat /sys/class/block/$disk/size)
    blocks=$((size / 8))
    cat /sys/class/block/$disk/size /sys/class/block/$disk/queue/logical_block_size /sys/class/block/$disk/device/model > "$dir/$disk.geometry"
    dd "if=/dev/$disk" "of=$dir/$disk.head" bs=4096 count=34 2>/dev/null
    dd "if=/dev/$disk" "of=$dir/$disk.tail" bs=4096 "skip=$((blocks-34))" count=34 2>/dev/null
done
cat /sys/class/block/sda16/uevent /sys/class/block/sda16/size > "$dir/userdata.txt"
cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted > "$dir/state.txt"
dmesg > "$dir/dmesg.txt"
sha256sum /dev/sda2 > "$dir/persist.sha256"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-check.txt"
sha256sum /dev/sde11 /dev/sde32 > "$dir/boot-logdump.sha256"
(cd "$dir" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf "/tmp/k109-layout-$prefix.tar" "k109-layout-$prefix"
sha256sum "/tmp/k109-layout-$prefix.tar"
echo LAYOUT_AND_FINAL_BOOT_GUARD_COMPLETE
