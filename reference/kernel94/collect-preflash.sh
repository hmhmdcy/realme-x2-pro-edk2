#!/bin/sh
set -eu
umask 077
dir=/tmp/k94-preflash
test ! -e "$dir"
[ "$(cat /proc/sys/kernel/random/boot_id)" = b65a234f-44f4-4ad3-9d40-ecafdeb233b1 ]
uname -a | grep -q '#92 SMP PREEMPT'
[ "$(cat /sys/class/block/sde/device/model)" = 'KLUDG4UHDB-B2D1 ' ]
grep -qx PARTNAME=boot /sys/class/block/sde11/uevent
grep -qx PARTNAME=logdump /sys/class/block/sde32/uevent
[ "$(cat /sys/class/block/sde11/size)" = 196608 ]
[ "$(cat /sys/class/block/sde32/size)" = 131072 ]
mkdir -m 700 "$dir"
dmesg > "$dir/dmesg.txt"
{
    uname -a
    cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted
    cat /sys/class/remoteproc/remoteproc0/state
    ls /sys/class/drm /sys/class/graphics
} > "$dir/state.txt"
if [ -f /sys/kernel/debug/dri/1/state ]; then
    cat /sys/kernel/debug/dri/1/state > "$dir/drm-state.txt"
else
    echo 'DRM absent before stage94' > "$dir/drm-state.txt"
fi
cat /sys/kernel/debug/devices_deferred > "$dir/devices-deferred.txt"
cat /proc/interrupts > "$dir/interrupts.txt"
cat /proc/modules > "$dir/modules.txt"
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/wpa-status.txt"
/usr/sbin/qrtr-lookup > "$dir/qrtr.txt"
cp /run/samurai-wifi-boot.log "$dir/"
for name in rmtfs.log tftp.log wpa-retry.log nv-source-hashes.txt; do cp "/run/samurai-wifi/$name" "$dir/"; done
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-source-check.txt"
grep -qx PARTNAME=persist /sys/class/block/sda2/uevent
[ "$(cat /sys/class/block/sda2/size)" = 65536 ]
[ "$(cat /sys/class/block/sda/device/model)" = 'KLUDG4UHDB-B2D1 ' ]
sha256sum /dev/sda2 > "$dir/persist-before.sha"
dd if=/dev/sde11 of=/tmp/k94-boot-partition-before.img bs=1048576
dd if=/dev/sde32 of=/tmp/k94-logdump-before.img bs=1048576
{
    cat /proc/sys/kernel/random/boot_id
    head -c 6682624 /dev/sde11 | sha256sum
    sha256sum /dev/sde11 /dev/sde32 /tmp/k94-boot-partition-before.img /tmp/k94-logdump-before.img
} > "$dir/guard.txt"
grep -q '^0974aafc6938726bb24f1bd92b11955bfffe824c3e0c27fa3e97029765fb5158 ' "$dir/guard.txt"
grep -q '^7905d198f229f44cfd279d14f044bf659b050be0baa02a3d1a5d67c135f9c4ee ' "$dir/guard.txt"
for file in /sys/fs/pstore/*; do [ -f "$file" ] || continue; cp "$file" "$dir/"; done
(cd "$dir" && sha256sum * > SHA256SUMS)
tar -C /tmp -cf /tmp/k94-preflash.tar k94-preflash
sha256sum /tmp/k94-preflash.tar /tmp/k94-boot-partition-before.img /tmp/k94-logdump-before.img
