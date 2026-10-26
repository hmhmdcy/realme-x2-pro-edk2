#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#97 SMP PREEMPT'
[ "$(cat /sys/class/block/sde/device/model)" = 'KLUDG4UHDB-B2D1 ' ]
grep -qx PARTNAME=boot /sys/class/block/sde11/uevent
grep -qx PARTNAME=logdump /sys/class/block/sde32/uevent
[ "$(cat /sys/class/block/sde11/size)" = 196608 ]
[ "$(cat /sys/class/block/sde32/size)" = 131072 ]
dir=/tmp/k99-preflash
test ! -e "$dir"
mkdir -m700 "$dir"
dmesg > "$dir/dmesg.txt"
{
    uname -a
    cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted
    cat /sys/class/remoteproc/remoteproc0/state
    ls /sys/class/drm /sys/class/graphics
    cat /sys/kernel/debug/dri/1/encoder-0/status
} > "$dir/state.txt"
cat /sys/kernel/debug/dri/1/state > "$dir/drm-state.txt"
cat /proc/interrupts > "$dir/interrupts.txt"
cat /proc/modules > "$dir/modules.txt"
ps > "$dir/processes.txt"
qrtr-lookup > "$dir/qrtr.txt"
cp /run/samurai-wifi-boot.log /run/samurai-bluetooth-boot.log "$dir/"
cp -a /tmp/k98-final-readonly-status "$dir/"
cp /tmp/k99-gpio-before.txt "$dir/"
cat /sys/kernel/debug/pinctrl/3100000.pinctrl/pinmux-pins > "$dir/pinmux-before.txt"
cp -a /run/samurai-radio-address "$dir/"
for name in rmtfs.log tftp.log wpa.log nv-source-hashes.txt; do cp "/run/samurai-wifi/$name" "$dir/"; done
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-source-check.txt"
sha256sum /dev/sda2 > "$dir/persist-before.sha"
dd if=/dev/sde11 of=/tmp/k99-boot-partition-before.img bs=1048576
dd if=/dev/sde32 of=/tmp/k99-logdump-before.img bs=1048576
{
    cat /proc/sys/kernel/random/boot_id
    head -c 6682624 /dev/sde11 | sha256sum
    sha256sum /dev/sde11 /dev/sde32 /tmp/k99-boot-partition-before.img /tmp/k99-logdump-before.img
} > "$dir/guard.txt"
grep -q '^0974aafc6938726bb24f1bd92b11955bfffe824c3e0c27fa3e97029765fb5158 ' "$dir/guard.txt"
grep -q '^0ebd3ec3ab41a70b86f03b09cff2dd0d9e39d0bcdf739b2fdf2c96d0694e0fc2 ' "$dir/guard.txt"
for file in /sys/fs/pstore/*; do test -f "$file" || continue; cp "$file" "$dir/"; done
(cd "$dir" && find . -type f ! -path './SHA256SUMS' -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k99-preflash.tar k99-preflash
sha256sum /tmp/k99-preflash.tar /tmp/k99-boot-partition-before.img /tmp/k99-logdump-before.img
echo PREFLASH_COMPLETE
