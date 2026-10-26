#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#99 SMP PREEMPT'
dir=/tmp/k100-automatic-start
test ! -e "$dir"
mkdir -m700 "$dir"
for attempt in $(seq 1 120); do
    if test -e /run/samurai-wifi/boot-finished && grep -q '^BT_ADDRESS_READY ' /run/samurai-bluetooth-boot.log; then break; fi
    sleep 2
done
cp /run/samurai-wifi-boot.log /run/samurai-bluetooth-boot.log "$dir/"
cp -a /run/samurai-radio-address "$dir/radio-address-before-manual"
cat /sys/class/net/wlan0/address > "$dir/wlan-before-manual.txt"
/tmp/k100-bt-mgmt-probe info > "$dir/bt-before-manual.txt"
{
    uname -a
    cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted
    cat /sys/class/remoteproc/remoteproc0/state
    ls /sys/class/drm /sys/class/graphics
} > "$dir/state.txt"
if ! grep -q ' /sys/kernel/debug debugfs ' /proc/mounts; then mount -t debugfs debugfs /sys/kernel/debug; fi
cat /sys/kernel/debug/dri/1/encoder-0/status > "$dir/display.txt"
cat /sys/bus/i2c/devices/1-005a/status > "$dir/haptics-status.txt"
dmesg > "$dir/dmesg.txt"
cp /run/samurai-wifi/boot-finished "$dir/"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-check.txt"
sha256sum /usr/sbin/samurai-wifi > "$dir/service-hash.txt"
grep -qx 0 /run/samurai-wifi/boot-finished
grep -qx WIFI_READY "$dir/samurai-wifi-boot.log"
grep -q '^RADIO_ADDRESS_QUERY_VERIFIED kind=wlan ' "$dir/samurai-wifi-boot.log"
grep -q '^RADIO_ADDRESS_QUERY_VERIFIED kind=bt ' "$dir/samurai-bluetooth-boot.log"
grep -qx 'BT_ADDRESS_VERIFIED index=0 powered=0 connectable=0 bondable=0' "$dir/samurai-bluetooth-boot.log"
grep -qx 'command=0x0003 status=0x00 payload=01000000' "$dir/bt-before-manual.txt"
grep -q '^id=97 go=00 state=00 .*active=0 starts=0 stops=0 watchdog_stops=0 error=0$' "$dir/haptics-status.txt"
test -e /sys/class/graphics/fb0
[ "$(cat /proc/sys/kernel/tainted)" = 0 ]
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = running ]
echo AUTOMATIC_ALL_SOURCE_READINESS_AND_HAPTICS_STANDBY_PASS > "$dir/result.txt"
(cd "$dir" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k100-automatic-start.tar k100-automatic-start
sha256sum /tmp/k100-automatic-start.tar
