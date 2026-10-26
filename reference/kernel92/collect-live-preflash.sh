#!/bin/sh
set -eu
umask 077
dir=/tmp/k92-live-preflash
test ! -e "$dir"
[ "$(cat /proc/sys/kernel/random/boot_id)" = e0b67ee9-b16d-49f7-9ffd-f0bcfca87496 ]
uname -a | grep -q '#90 SMP PREEMPT'
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline ]
[ "$(cat /sys/class/block/sde/device/model)" = 'KLUDG4UHDB-B2D1 ' ]
grep -qx PARTNAME=boot /sys/class/block/sde11/uevent
grep -qx PARTNAME=logdump /sys/class/block/sde32/uevent
[ "$(cat /sys/class/block/sde11/size)" = 196608 ]
[ "$(cat /sys/class/block/sde32/size)" = 131072 ]
mkdir -m 700 "$dir"
mount -t debugfs debugfs /sys/kernel/debug 2>/dev/null || true
mount -t pstore pstore /sys/fs/pstore 2>/dev/null || true
dmesg > "$dir/dmesg.txt"
{
    uname -a
    cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted
    cat /sys/class/remoteproc/remoteproc0/state
    cat /sys/kernel/debug/dri/1/encoder-0/status
} > "$dir/state.txt"
cat /sys/kernel/debug/dri/1/state > "$dir/drm-state.txt"
for file in /sys/fs/pstore/*; do
    [ -f "$file" ] || continue
    cp "$file" "$dir/"
done
dd if=/dev/sde11 of="$dir/boot-partition-before.img" bs=1048576
dd if=/dev/sde32 of="$dir/logdump-before.img" bs=1048576
{
    cat /proc/sys/kernel/random/boot_id
    cat /sys/class/remoteproc/remoteproc0/state
    head -c 6682624 /dev/sde11 | sha256sum
    sha256sum /dev/sde11 /dev/sde32 "$dir/boot-partition-before.img" "$dir/logdump-before.img"
} > "$dir/guard.txt"
grep -q '^ed7ba3a76892fa2dd276daef3bc66c14c0737f49d385ae840a397fdfae39e396 ' "$dir/guard.txt"
grep -q '^37ea81b0c2dbc678ed090048fcad8160acd089f1b7189eddbf0d0c873698ac36 ' "$dir/guard.txt"
(cd "$dir" && sha256sum * > SHA256SUMS)
tar -C /tmp -cf /tmp/k92-live-preflash.tar k92-live-preflash
sha256sum /tmp/k92-live-preflash.tar
