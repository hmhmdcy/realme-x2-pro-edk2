#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#95 SMP PREEMPT'
for phase in initial-retry1 recovery five-ghz; do
    grep -qx COEXISTENCE_OBSERVATION_PASS "/tmp/k96-$phase-coexistence.log"
done
grep -qx HOT_CYCLE_RECOVERY_PASS /tmp/k96-hot-cycle.log
for phase in initial recovery five-ghz; do
    grep -qx NETWORK_OBSERVATION_PASS "/tmp/k96-$phase-network.log"
done
dir=/tmp/k96-checkpoint-final
test ! -e "$dir"
mkdir -m 700 "$dir" "$dir/queries" "$dir/tests" "$dir/services"
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
cat /sys/class/net/wlan0/address > "$dir/wlan-address.txt"
/tmp/k96-bt-mgmt-probe info > "$dir/bt-info.txt"
/usr/sbin/samurai-bluetooth status > "$dir/bluetooth-service-status.txt"
cp /run/samurai-wifi-boot.log /run/samurai-bluetooth-boot.log "$dir/"
cp /run/samurai-wifi/boot-started /run/samurai-wifi/boot-finished "$dir/"
for name in rmtfs.log tftp.log wpa.log dhcp-lease.txt nv-source-hashes.txt; do cp "/run/samurai-wifi/$name" "$dir/services/"; done
for name in initial initial-retry1 hot-cycle initial-coexistence initial-retry1-coexistence recovery-coexistence five-ghz-coexistence initial-network recovery-network five-ghz-network five-ghz; do
    cp -a "/tmp/k96-$name" "$dir/tests/"
done
for file in /tmp/k96-*.log /tmp/k96-*-traffic-sha.txt /tmp/k96-*-traffic-wpa.txt /tmp/k96-*-traffic-dhcp.txt; do
    test -f "$file" || continue
    cp "$file" "$dir/tests/"
done
for file in /tmp/k96-verified-*.bin; do cp "$file" "$dir/queries/"; done
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-source-check.txt"
sha256sum -c /tmp/k96-persist-before.sha > "$dir/persist-check.txt"
{
    head -c 6682624 /dev/sde11 | sha256sum
    sha256sum /dev/sde11 /dev/sde32 /init /usr/sbin/samurai-bluetooth /lib/modules/samurai/*.ko /tmp/k96-dms-mac-read /tmp/k96-bt-mgmt-probe
} > "$dir/deployment-readback.txt"
for file in /sys/fs/pstore/*; do test -f "$file" || continue; cp "$file" "$dir/"; done
(cd "$dir" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k96-checkpoint-final.tar k96-checkpoint-final
sha256sum /tmp/k96-checkpoint-final.tar
echo CHECKPOINT_COMPLETE
