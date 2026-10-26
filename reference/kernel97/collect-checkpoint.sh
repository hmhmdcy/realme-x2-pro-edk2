#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#96 SMP PREEMPT'
grep -qx AUTO_ADDRESS_BOOT_PASS /tmp/k97-initial/auto-address-result.txt
grep -qx WIFI_ONLY_OBSERVATION_PASS /tmp/k97-wifi-only.log
for phase in initial-retry1 five-ghz; do
    grep -qx COEXISTENCE_OBSERVATION_PASS "/tmp/k97-$phase-coexistence.log"
done
for phase in initial-retry1 five-ghz-retry1; do
    grep -qx NETWORK_OBSERVATION_PASS "/tmp/k97-$phase-network.log"
done
dir=/tmp/k97-checkpoint-final
test ! -e "$dir"
mkdir -m700 "$dir" "$dir/tests" "$dir/services"
/tmp/k97-bt-mgmt-probe off > "$dir/bt-off.txt"
/tmp/k97-bt-mgmt-probe info > "$dir/bt-info-final.txt"
/usr/sbin/samurai-radio-address status > "$dir/radio-address-status.txt"
cp -a /run/samurai-radio-address "$dir/radio-address"
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
qrtr-lookup > "$dir/qrtr.txt"
wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/wpa-status.txt"
iw dev wlan0 link > "$dir/iw-link.txt"
cat /sys/class/net/wlan0/address > "$dir/wlan-address.txt"
cp /run/samurai-wifi-boot.log /run/samurai-bluetooth-boot.log "$dir/"
cp /run/samurai-wifi/boot-started /run/samurai-wifi/boot-finished "$dir/"
for name in rmtfs.log tftp.log wpa.log dhcp-lease.txt nv-source-hashes.txt; do cp "/run/samurai-wifi/$name" "$dir/services/"; done
for name in initial first-disconnect initial-coexistence initial-network wifi-only initial-retry1-network initial-retry1-coexistence five-ghz five-ghz-network five-ghz-retry1-network five-ghz-coexistence; do
    cp -a "/tmp/k97-$name" "$dir/tests/"
done
for file in /tmp/k97-*.log /tmp/k97-*-traffic-sha.txt /tmp/k97-*-traffic-wpa.txt /tmp/k97-*-traffic-dhcp.txt /tmp/k97-retry1-bt*.txt; do
    test -f "$file" || continue
    cp "$file" "$dir/tests/"
done
cp /tmp/k97-first-disconnect.tar "$dir/tests/"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-source-check.txt"
sha256sum -c /tmp/k97-persist-before.sha > "$dir/persist-check.txt"
{
    head -c 6682624 /dev/sde11 | sha256sum
    sha256sum /dev/sde11 /dev/sde32 /init /usr/sbin/samurai-wifi /usr/sbin/samurai-bluetooth /usr/sbin/samurai-radio-address /usr/sbin/samurai-dms-mac-read /usr/sbin/samurai-bt-address /lib/modules/samurai/*.ko
} > "$dir/deployment-readback.txt"
for file in /sys/fs/pstore/*; do test -f "$file" || continue; cp "$file" "$dir/"; done
(cd "$dir" && find . -type f ! -path './SHA256SUMS' -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k97-checkpoint-final.tar k97-checkpoint-final
sha256sum /tmp/k97-checkpoint-final.tar
echo CHECKPOINT_COMPLETE
