#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#97 SMP PREEMPT'
grep -qx AUTO_INDEPENDENT_ADDRESSES_BOOT_PASS /tmp/k98-automatic-addresses/result.txt
grep -qx TRACE_CONNECTIVITY_CAPTURE_PASS /tmp/k98-trace-connectivity/result.txt
for phase in initial-retry1 five-ghz; do
    grep -qx WIFI_TX_BYTES=4194304 "/tmp/k98-$phase-traffic-server.log"
    grep -qx WIFI_RX_BYTES=4194304 "/tmp/k98-$phase-traffic-server.log"
done
dir=/tmp/k98-checkpoint-final
test ! -e "$dir"
mkdir -m700 "$dir" "$dir/tests" "$dir/services"
/tmp/k98-bt-mgmt-probe off > "$dir/bt-off.txt"
/tmp/k98-bt-mgmt-probe info > "$dir/bt-info.txt"
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
cp /run/samurai-wifi-boot.log /run/samurai-bluetooth-boot.log "$dir/"
cp -a /run/samurai-radio-address "$dir/"
cp /run/samurai-wifi/boot-finished "$dir/"
/usr/sbin/samurai-radio-address status > "$dir/address-status.txt"
wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/wpa-status.txt"
iw dev wlan0 link > "$dir/iw-link.txt"
cat /sys/class/net/wlan0/address > "$dir/wlan-address.txt"
for name in rmtfs.log tftp.log wpa.log dhcp-lease.txt nv-source-hashes.txt; do cp "/run/samurai-wifi/$name" "$dir/services/"; done
for name in automatic-addresses trace-connectivity initial-network five-ghz-network two-ghz-data final-five-ghz; do cp -a "/tmp/k98-$name" "$dir/tests/"; done
for file in /tmp/k98-*-traffic-sha.txt /tmp/k98-*-traffic-server.log /tmp/k98-*-traffic-wpa.txt /tmp/k98-*-traffic-dhcp.txt; do test -f "$file" || continue; cp "$file" "$dir/tests/"; done
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-source-check.txt"
sha256sum -c /tmp/k98-persist-before.sha > "$dir/persist-check.txt"
{
    head -c 6682624 /dev/sde11 | sha256sum
    sha256sum /dev/sde11 /dev/sde32 /init /usr/sbin/samurai-radio-address /usr/sbin/samurai-wifi /usr/sbin/samurai-bluetooth /usr/sbin/samurai-dms-mac-read /usr/sbin/samurai-bt-address /lib/modules/samurai/*.ko
} > "$dir/deployment-readback.txt"
for file in /sys/fs/pstore/*; do test -f "$file" || continue; cp "$file" "$dir/"; done
(cd "$dir" && find . -type f ! -path './SHA256SUMS' -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k98-checkpoint-final.tar k98-checkpoint-final
sha256sum /tmp/k98-checkpoint-final.tar
echo CHECKPOINT_COMPLETE
