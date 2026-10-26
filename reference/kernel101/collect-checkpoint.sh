#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#100 SMP PREEMPT'
mpss=$(/usr/sbin/samurai-modem-remoteproc)
[ "$(cat "$mpss/state")" = running ]
adsp=$(cat /tmp/k101-audio-runtime/adsp-path.txt)
[ "$(cat "$adsp/state")" = running ]
grep -qx 1 /run/samurai-wifi/boot-finished
grep -qx BOUNDED_MANUAL_RECOVERY_AFTER_AUTO_MPSS_CRASH_PASS /tmp/k101-radio-recovery-first/result.txt
grep -qx MANUAL_AFTER_CRASH_5G_AUTH_DHCP_GATEWAY_DNS_HTTP_PASS /tmp/k101-recovered-network-retry1/result.txt
dir=/tmp/k101-checkpoint-retry1
test ! -e "$dir"
mkdir -m700 "$dir" "$dir/tests"
mountpoint -q /sys/kernel/debug || mount -t debugfs debugfs /sys/kernel/debug
{
    uname -a
    cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted
    cat "$mpss/state" "$adsp/state"
} > "$dir/state.txt"
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/wifi-status.txt"
grep -qx wpa_state=COMPLETED "$dir/wifi-status.txt"
grep -qx freq=5180 "$dir/wifi-status.txt"
/tmp/k101-bt-mgmt-probe info > "$dir/bt-info.txt"
grep -qx 'command=0x0003 status=0x00 payload=01000000' "$dir/bt-info.txt"
cat /sys/bus/aprbus/devices/*/samurai_api > "$dir/native-api.txt"
cat /proc/asound/cards > "$dir/alsa-cards.txt"
cat /sys/bus/i2c/devices/1-005a/status > "$dir/haptics-status.txt"
cat /sys/kernel/debug/dri/1/encoder-0/status > "$dir/encoder-status.txt"
cat /proc/modules > "$dir/modules.txt"
cat /proc/mounts > "$dir/mounts.txt"
ps > "$dir/processes.txt"
/usr/sbin/qrtr-lookup > "$dir/qrtr.txt"
for bus in rpmsg aprbus; do
    for node in /sys/bus/$bus/devices/*; do
        test -e "$node" || continue
        echo "$node"
        test ! -L "$node/driver" || readlink "$node/driver"
    done
done > "$dir/audio-bus.txt"
/usr/sbin/samurai-radio-address status > "$dir/address-status.txt"
cp -a /run/samurai-radio-address "$dir/"
cp /run/samurai-wifi-boot.log /run/samurai-bluetooth-boot.log "$dir/"
cp /run/samurai-wifi/boot-finished /run/samurai-wifi/nv-source-hashes.txt "$dir/"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-source-check.txt"
sha256sum /dev/sda2 > "$dir/persist-after.sha"
sha256sum /dev/sde11 /dev/sde32 /init /usr/sbin/samurai-* /lib/modules/samurai/*.ko > "$dir/deployment.sha"
cp /sys/firmware/fdt "$dir/runtime-fdt.bin"
cp -a /tmp/k101-audio-runtime /tmp/k101-first-boot-failure /tmp/k101-radio-recovery-first /tmp/k101-recovered-network /tmp/k101-recovered-network-retry1 "$dir/tests/"
dmesg > "$dir/dmesg.txt"
[ "$(cat /proc/sys/kernel/tainted)" = 0 ]
echo ADSP_NATIVE_REPLY_AND_MANUAL_5G_CHECKPOINT_PASS > "$dir/result.txt"
(cd "$dir" && find . -type f ! -path ./SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k101-checkpoint-retry1.tar k101-checkpoint-retry1
sha256sum /tmp/k101-checkpoint-retry1.tar
