#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#97 SMP PREEMPT'
dir=/tmp/k98-automatic-addresses
test ! -e "$dir"
mkdir -m700 "$dir"
chmod 700 /tmp/k98-bt-mgmt-probe
if ! grep -q ' /sys/kernel/debug debugfs ' /proc/mounts; then mount -t debugfs debugfs /sys/kernel/debug; fi
if ! test -r /sys/kernel/tracing/available_events; then mount -t tracefs tracefs /sys/kernel/tracing; fi
for attempt in $(seq 1 120); do
    test -e /run/samurai-wifi/boot-finished && grep -q '^BT_ADDRESS_READY ' /run/samurai-bluetooth-boot.log && break
    sleep 2
done
cp /run/samurai-wifi-boot.log /run/samurai-bluetooth-boot.log "$dir/"
cp -a /run/samurai-radio-address "$dir/radio-address-before-manual"
cat /sys/class/net/wlan0/address > "$dir/wlan-before-manual.txt"
/tmp/k98-bt-mgmt-probe info > "$dir/bt-before-manual.txt"
cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted /sys/class/remoteproc/remoteproc0/state > "$dir/state.txt"
cat /sys/kernel/debug/dri/1/encoder-0/status > "$dir/display.txt"
dmesg > "$dir/dmesg.txt"
cat /sys/kernel/tracing/available_events > "$dir/available-events.txt"
grep -qx 0 /run/samurai-wifi/boot-finished
grep -q '^RADIO_ADDRESS_QUERY_VERIFIED kind=wlan ' "$dir/samurai-wifi-boot.log"
grep -q '^RADIO_ADDRESS_QUERY_VERIFIED kind=bt ' "$dir/samurai-bluetooth-boot.log"
grep -qx 'BT_ADDRESS_VERIFIED index=0 powered=0 connectable=0 bondable=0' "$dir/samurai-bluetooth-boot.log"
grep -qx 'command=0x0003 status=0x00 payload=01000000' "$dir/bt-before-manual.txt"
test -e /sys/class/graphics/fb0
grep -qx 'ath10k:ath10k_log_dbg' "$dir/available-events.txt"
[ "$(cat /proc/sys/kernel/tainted)" = 0 ]
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = running ]
/usr/sbin/samurai-radio-address status > "$dir/address-status.txt"
echo AUTO_INDEPENDENT_ADDRESSES_BOOT_PASS > "$dir/result.txt"
(cd "$dir" && find . -type f ! -path './SHA256SUMS' -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k98-automatic-addresses.tar k98-automatic-addresses
sha256sum /tmp/k98-automatic-addresses.tar
