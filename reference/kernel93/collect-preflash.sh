#!/bin/sh
set -eu
umask 077
dir=/tmp/k93-preflash
test ! -e "$dir"
[ "$(cat /proc/sys/kernel/random/boot_id)" = 7198e2c9-17e4-42af-ac12-71a2013b5ea8 ]
uname -a | grep -q '#91 SMP PREEMPT'
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
cp /run/samurai-wifi-boot.log /run/samurai-wifi-fixed.log "$dir/"
for name in rmtfs.log tftp.log wpa.log firmware-check.txt nv-after-start.txt nv-source-hashes.txt; do cp "/run/samurai-wifi/$name" "$dir/"; done
for file in /tmp/k92-bt-*.txt /tmp/k92-nfc-*.txt /tmp/k92-persist-before.sha /tmp/k92-pretest-bt.log /tmp/k92-network-test2.txt /tmp/k92-traffic-server-final.log; do cp "$file" "$dir/"; done
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/wpa-status.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-source-check.txt"
sha256sum -c /tmp/k92-persist-before.sha > "$dir/persist-check.txt"
sha256sum /tmp/k92-traffic.bin /tmp/k92-traffic-upload.bin > "$dir/traffic-sha256.txt"
dd if=/dev/sde11 of=/tmp/k93-boot-partition-before.img bs=1048576
dd if=/dev/sde32 of=/tmp/k93-logdump-before.img bs=1048576
{
    cat /proc/sys/kernel/random/boot_id
    head -c 6682624 /dev/sde11 | sha256sum
    sha256sum /dev/sde11 /dev/sde32 /tmp/k93-boot-partition-before.img /tmp/k93-logdump-before.img
} > "$dir/guard.txt"
grep -q '^35f6fe338f2fb21ec15702e5c532d742dd6dafd90d11d5cbed8ded2348b1885c ' "$dir/guard.txt"
grep -q '^7972dae9d5f3c709fd41f8b0e577417e1f6278930afa04762bae70dbb85ace86 ' "$dir/guard.txt"
(cd "$dir" && sha256sum * > SHA256SUMS)
tar -C /tmp -cf /tmp/k93-preflash.tar k93-preflash
sha256sum /tmp/k93-preflash.tar /tmp/k93-boot-partition-before.img /tmp/k93-logdump-before.img
