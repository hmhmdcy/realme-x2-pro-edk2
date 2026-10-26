#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#100 SMP PREEMPT'
tr '\0' '\n' < /proc/device-tree/compatible | grep -qx realme,samurai
[ "$(cat /sys/class/block/sde/device/model)" = 'KLUDG4UHDB-B2D1 ' ]
[ "$(cat /sys/class/block/sda/device/model)" = 'KLUDG4UHDB-B2D1 ' ]
grep -qx PARTNAME=dtbo /sys/class/block/sde17/uevent
grep -qx PARTNAME=vendor /sys/class/block/sda9/uevent
[ "$(cat /sys/class/block/sde17/size)" = 49152 ]
[ "$(cat /sys/class/block/sda9/size)" = 3342336 ]
dir=/tmp/k102-stock-audio-contract
test ! -e "$dir"
mkdir -m700 "$dir" "$dir/vendor" "$dir/mount-vendor"
trap 'mountpoint -q "$dir/mount-vendor" && umount "$dir/mount-vendor" || true' EXIT
{
    uname -a
    cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted
    for p in /sys/class/remoteproc/remoteproc*; do cat "$p/name" "$p/state"; done
} > "$dir/state.txt"
sha256sum /dev/sde17 > "$dir/dtbo-before.sha"
dd if=/dev/sde17 of=/tmp/k102-stock-dtbo.img bs=1048576
sha256sum /tmp/k102-stock-dtbo.img /dev/sde17 > "$dir/dtbo-after.sha"
gzip -1 -c /tmp/k102-stock-dtbo.img > "$dir/stock-dtbo.img.gz"
mount -t ext4 -o ro,noload,nosuid,nodev,noexec /dev/sda9 "$dir/mount-vendor"
cat /proc/mounts > "$dir/mounts-during.txt"
(cd "$dir/mount-vendor" && find etc -type f | sort) > "$dir/vendor-etc-files.txt"
for p in "$dir/mount-vendor"/etc/*audio* "$dir/mount-vendor"/etc/*mixer* "$dir/mount-vendor"/etc/sound_trigger* "$dir/mount-vendor"/build.prop; do
    test -f "$p" || continue
    test ! -L "$p"
    rel=${p#"$dir/mount-vendor/"}
    mkdir -p "$dir/vendor/$(dirname "$rel")"
    cp "$p" "$dir/vendor/$rel"
done
for p in "$dir/mount-vendor"/lib64/hw/audio.primary*.so; do
    test -f "$p" || continue
    test ! -L "$p"
    mkdir -p "$dir/vendor/lib64/hw"
    cp "$p" "$dir/vendor/lib64/hw/$(basename "$p")"
done
umount "$dir/mount-vendor"
cat /proc/mounts > "$dir/mounts-after.txt"
mountpoint -q /sys/kernel/debug || mount -t debugfs debugfs /sys/kernel/debug
cat /sys/kernel/debug/pinctrl/3100000.pinctrl/pinmux-pins > "$dir/pinmux.txt"
cat /sys/bus/i2c/devices/1-005a/status > "$dir/haptics-status.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-check.txt"
sha256sum /dev/sda2 > "$dir/persist.sha"
dmesg > "$dir/dmesg.txt"
(cd "$dir" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k102-stock-audio-contract.tar k102-stock-audio-contract
sha256sum /tmp/k102-stock-audio-contract.tar
