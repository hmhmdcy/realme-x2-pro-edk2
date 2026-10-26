#!/bin/sh
set -eu
umask 077
dir=/tmp/k95-checkpoint-final
test ! -e "$dir"
[ "$(cat /proc/sys/kernel/random/boot_id)" = 02ba5ffd-9768-43e4-9c6e-511bb1aeccd1 ]
grep -q COEXISTENCE_OBSERVATION_PASS /tmp/k95-coexistence.log
for attempt in $(seq 1 90); do
    grep -q COEXISTENCE_OBSERVATION_PASS /tmp/k95-5ghz-coexistence.log && break
    sleep 1
done
grep -q COEXISTENCE_OBSERVATION_PASS /tmp/k95-5ghz-coexistence.log
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
/usr/sbin/qrtr-lookup > "$dir/qrtr.txt"
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/wpa-status.txt"
/usr/sbin/iw dev wlan0 link > "$dir/iw-link.txt"
cp /run/samurai-wifi-boot.log /run/samurai-bluetooth-boot.log "$dir/"
for name in rmtfs.log tftp.log wpa.log dhcp-lease.txt nv-source-hashes.txt; do cp "/run/samurai-wifi/$name" "$dir/"; done
for file in /tmp/k95-bt-*.txt /tmp/k95-*dmesg.txt /tmp/k95-test-connectivity.log /tmp/k95-nfc-controller.txt /tmp/k95-2ghz-*.txt /tmp/k95-display-*.txt /tmp/k95-drm-*.txt /tmp/k95-coexistence*.txt /tmp/k95-coexistence.log /tmp/k95-5ghz-*.txt /tmp/k95-5ghz-*.log /tmp/k95-traffic-server.log /tmp/k95-traffic-sha.txt; do
    [ -f "$file" ] || continue
    cp "$file" "$dir/"
done
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-source-check.txt"
sha256sum -c /tmp/k95-persist-before.sha > "$dir/persist-check.txt"
{
    head -c 6682624 /dev/sde11 | sha256sum
    sha256sum /dev/sde11 /dev/sde32 /usr/sbin/samurai-bluetooth /lib/modules/samurai/*.ko
} > "$dir/deployment-readback.txt"
for file in /sys/fs/pstore/*; do [ -f "$file" ] || continue; cp "$file" "$dir/"; done
(cd "$dir" && sha256sum * > SHA256SUMS)
tar -C /tmp -cf /tmp/k95-checkpoint-final.tar k95-checkpoint-final
sha256sum /tmp/k95-checkpoint-final.tar
