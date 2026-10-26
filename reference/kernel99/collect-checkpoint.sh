#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#98 SMP PREEMPT'
grep -qx RADIO_RAM_RECOVERY_PASS /tmp/k99-radio-ram-recovery/result.txt
grep -qx MANUAL_RECOVERY_5G_AUTH_DHCP_GATEWAY_DNS_HTTP_PASS /tmp/k99-restored-network-retry1/result.txt
grep -qx HAPTICS_CLOSE_KILL_WATCHDOG_PASS /tmp/k99-haptics-lifecycle/result.txt
dir=/tmp/k99-checkpoint-final
test ! -e "$dir"
mkdir -m700 "$dir" "$dir/tests" "$dir/services"
/tmp/k99-bt-mgmt-probe info > "$dir/bt-info.txt"
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
cat /sys/bus/i2c/devices/1-005a/status > "$dir/haptics-status.txt"
cat /proc/bus/input/devices > "$dir/input-devices.txt"
cp /run/samurai-wifi-boot.log /run/samurai-bluetooth-boot.log "$dir/"
cp -a /run/samurai-radio-address "$dir/"
cp /run/samurai-wifi/boot-finished "$dir/"
/usr/sbin/samurai-radio-address status > "$dir/address-status.txt"
wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/wpa-status.txt"
iw dev wlan0 link > "$dir/iw-link.txt"
cat /sys/class/net/wlan0/address > "$dir/wlan-address.txt"
for name in rmtfs.log tftp.log wpa.log dhcp-lease.txt nv-source-hashes.txt; do cp "/run/samurai-wifi/$name" "$dir/services/"; done
for name in haptics-initial haptics-initial-retry1 haptics-lifecycle radio-ram-recovery restored-network restored-network-retry1 first-wifi-state; do
    cp -a "/tmp/k99-$name" "$dir/tests/"
done
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-source-check.txt"
sha256sum -c /tmp/k99-persist-before.sha > "$dir/persist-check.txt"
{
    head -c 6680576 /dev/sde11 | sha256sum
    sha256sum /dev/sde11 /dev/sde32 /init /usr/sbin/samurai-radio-address /usr/sbin/samurai-wifi /usr/sbin/samurai-bluetooth /usr/sbin/samurai-dms-mac-read /usr/sbin/samurai-bt-address /lib/modules/samurai/*.ko
} > "$dir/deployment-readback.txt"
ps > "$dir/processes.txt"
for file in /sys/fs/pstore/*; do test -f "$file" || continue; cp "$file" "$dir/"; done
(cd "$dir" && find . -type f ! -path './SHA256SUMS' -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k99-checkpoint-final.tar k99-checkpoint-final
sha256sum /tmp/k99-checkpoint-final.tar
echo CHECKPOINT_COMPLETE
