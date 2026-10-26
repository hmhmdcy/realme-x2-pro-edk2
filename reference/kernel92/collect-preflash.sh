#!/bin/sh
set -eu
umask 077
dir=/tmp/k92-preflash-final
test ! -e "$dir"
[ "$(cat /proc/sys/kernel/random/boot_id)" = 7ed1ff99-4a7d-459c-b3e0-3f4e20a982ac ]
uname -a | grep -q '#90 SMP PREEMPT'
[ "$(cat /sys/class/block/sde/device/model)" = 'KLUDG4UHDB-B2D1 ' ]
grep -qx PARTNAME=boot /sys/class/block/sde11/uevent
grep -qx PARTNAME=logdump /sys/class/block/sde32/uevent
[ "$(cat /sys/class/block/sde11/size)" = 196608 ]
[ "$(cat /sys/class/block/sde32/size)" = 131072 ]
mount -t debugfs debugfs /sys/kernel/debug 2>/dev/null || true
mount -t tracefs tracefs /sys/kernel/tracing 2>/dev/null || true
mkdir -m 700 "$dir"
dmesg > "$dir/dmesg.txt"
{
    uname -a
    cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted
    cat /sys/class/remoteproc/remoteproc0/state
    cat /sys/kernel/debug/dri/1/encoder-0/status
} > "$dir/state.txt"
cat /sys/kernel/debug/dri/1/state > "$dir/drm-state.txt"
for name in trace snapshot; do
    if [ -f "/sys/kernel/tracing/instances/display/$name" ]; then
        cat "/sys/kernel/tracing/instances/display/$name" > "$dir/display-$name.txt"
    else
        echo 'No display trace instance in this boot; previous private snapshots retained' > "$dir/display-$name.txt"
    fi
done
cp /tmp/k92-previous-boot-console.txt "$dir/"
cp /run/samurai-wifi-pretest.log "$dir/"
for name in rmtfs.log tftp.log wpa.log firmware-check.txt nv-after-start.txt; do
    cp "/run/samurai-wifi/$name" "$dir/"
done
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/wpa-status.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-source-check.txt"
dd if=/dev/sde11 of=/tmp/k92-boot-partition-before.img bs=1048576
dd if=/dev/sde32 of=/tmp/k92-logdump-before.img bs=1048576
{
    cat /proc/sys/kernel/random/boot_id
    head -c 6682624 /dev/sde11 | sha256sum
    sha256sum /dev/sde11 /dev/sde32 /tmp/k92-boot-partition-before.img /tmp/k92-logdump-before.img
} > "$dir/partition-hashes.txt"
grep -q '^6c2ee20360acd9a535004cef05c2d6d7ab207936cec56038746d87e6ca16cd23 ' "$dir/partition-hashes.txt"
grep -q '^37ea81b0c2dbc678ed090048fcad8160acd089f1b7189eddbf0d0c873698ac36 ' "$dir/partition-hashes.txt"
(cd "$dir" && sha256sum * > SHA256SUMS)
tar -C /tmp -cf /tmp/k92-preflash.tar k92-preflash-final
sha256sum /tmp/k92-preflash.tar /tmp/k92-boot-partition-before.img /tmp/k92-logdump-before.img
