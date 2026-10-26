#!/bin/sh
set -eu
umask 077
dir=/tmp/k95-preflash
test ! -e "$dir"
[ "$(cat /proc/sys/kernel/random/boot_id)" = 4cc1a6f8-d033-4608-bdd9-98e97a0df439 ]
uname -a | grep -q '#93 SMP PREEMPT'
for attempt in $(seq 1 90); do
    grep -q COEXISTENCE_OBSERVATION_PASS /tmp/k94-coexistence.log && break
    sleep 1
done
grep -q COEXISTENCE_OBSERVATION_PASS /tmp/k94-coexistence.log
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
    cat /sys/kernel/debug/dri/1/encoder-0/status
} > "$dir/state.txt"
cat /sys/kernel/debug/dri/1/state > "$dir/drm-state.txt"
cat /sys/kernel/debug/devices_deferred > "$dir/devices-deferred.txt"
cat /proc/interrupts > "$dir/interrupts.txt"
cat /proc/modules > "$dir/modules.txt"
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/wpa-status.txt"
/usr/sbin/qrtr-lookup > "$dir/qrtr.txt"
cp /run/samurai-wifi-boot.log /run/samurai-bluetooth-boot.log "$dir/"
for name in rmtfs.log tftp.log wpa.log nv-source-hashes.txt; do cp "/run/samurai-wifi/$name" "$dir/"; done
for file in /tmp/k94-bt-*.txt /tmp/k94-bt-autoload-failed.log /tmp/k94-test-connectivity*.log /tmp/k94-nfc-controller.txt /tmp/k94-2ghz-*.txt /tmp/k94-display-*.txt /tmp/k94-drm-*.txt /tmp/k94-*dmesg.txt /tmp/k94-coexistence*.txt /tmp/k94-coexistence.log /tmp/k94-traffic-server.log /tmp/k94-traffic-sha.txt; do cp "$file" "$dir/"; done
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-source-check.txt"
sha256sum -c /tmp/k94-persist-before.sha > "$dir/persist-check.txt"
cp /tmp/k94-persist-before.sha "$dir/persist-before.sha"
dd if=/dev/sde11 of=/tmp/k95-boot-partition-before.img bs=1048576
dd if=/dev/sde32 of=/tmp/k95-logdump-before.img bs=1048576
{
    cat /proc/sys/kernel/random/boot_id
    head -c 6682624 /dev/sde11 | sha256sum
    sha256sum /dev/sde11 /dev/sde32 /tmp/k95-boot-partition-before.img /tmp/k95-logdump-before.img
} > "$dir/guard.txt"
grep -q '^0974aafc6938726bb24f1bd92b11955bfffe824c3e0c27fa3e97029765fb5158 ' "$dir/guard.txt"
grep -q '^7ea0b8a9706f8c3f60e9e982a2cf71f20ee4372b5d32ea30275c092a572bfc29 ' "$dir/guard.txt"
for file in /sys/fs/pstore/*; do [ -f "$file" ] || continue; cp "$file" "$dir/"; done
(cd "$dir" && sha256sum * > SHA256SUMS)
tar -C /tmp -cf /tmp/k95-preflash.tar k95-preflash
sha256sum /tmp/k95-preflash.tar /tmp/k95-boot-partition-before.img /tmp/k95-logdump-before.img
