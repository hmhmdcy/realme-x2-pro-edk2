#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#96 SMP PREEMPT'
dir=/tmp/k97-initial
test ! -e "$dir"
mkdir -m 700 "$dir"
if ! grep -q ' /sys/kernel/debug debugfs ' /proc/mounts; then mount -t debugfs debugfs /sys/kernel/debug; fi
for attempt in $(seq 1 90); do
    if test -e /run/samurai-wifi/boot-finished &&
       grep -q '^BT_ADDRESS_READY ' /run/samurai-bluetooth-boot.log; then break; fi
    sleep 2
done
grep -qx 0 /run/samurai-wifi/boot-finished
grep -q '^RADIO_ADDRESS_QUERY_VERIFIED ' /run/samurai-wifi-boot.log
grep -q '^WLAN_ADDRESS_VERIFIED ' /run/samurai-wifi-boot.log
grep -q '^BT_ADDRESS_VERIFIED index=0 powered=0 connectable=0 bondable=0$' /run/samurai-bluetooth-boot.log
grep -q '^BT_ADDRESS_READY ' /run/samurai-bluetooth-boot.log
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = running ]
[ "$(cat /proc/sys/kernel/tainted)" = 0 ]
test -e /sys/class/graphics/fb0
cp /run/samurai-wifi-boot.log /run/samurai-bluetooth-boot.log "$dir/"
cp -a /run/samurai-radio-address "$dir/radio-address-before-manual"
cat /sys/class/net/wlan0/address > "$dir/wlan-address-before-manual.txt"
chmod 700 /tmp/k97-bt-mgmt-probe /tmp/k97-wifi-traffic-server
/tmp/k97-bt-mgmt-probe info > "$dir/bt-info-before-manual.txt"
grep -qx 'command=0x0003 status=0x00 payload=01000000' "$dir/bt-info-before-manual.txt"
query=$(cat /run/samurai-radio-address/current)
mac=$(od -An -tx1 -v "$query/wlan-mac-le.bin" | awk '{printf "%s:%s:%s:%s:%s:%s",$6,$5,$4,$3,$2,$1}')
[ "$(cat /sys/class/net/wlan0/address)" = "$mac" ]
unset mac
/usr/sbin/samurai-radio-address wlan > "$dir/wlan-idempotent.txt" 2>&1
/usr/sbin/samurai-radio-address bt > "$dir/bt-idempotent.txt" 2>&1
echo AUTO_ADDRESS_BOOT_PASS > "$dir/auto-address-result.txt"
cat /sys/kernel/debug/dri/1/encoder-0/status > "$dir/display-before.txt"
cp /tmp/k97-wpa-test-private.conf /run/samurai-wifi/wpa.conf
chmod 600 /run/samurai-wifi/wpa.conf
cli() { /usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 "$@"; }
cli reconfigure | grep -qx OK
for attempt in $(seq 1 30); do
    cli status > "$dir/status-after.txt"
    if grep -qx wpa_state=COMPLETED "$dir/status-after.txt" && grep -qx freq=2462 "$dir/status-after.txt"; then break; fi
    sleep 2
done
grep -qx wpa_state=COMPLETED "$dir/status-after.txt"
grep -qx freq=2462 "$dir/status-after.txt"
udhcpc -i wlan0 -s /usr/sbin/samurai-udhcpc-wlan -n -q -t 5 -T 3 > "$dir/dhcp.txt" 2>&1
/tmp/k97-bt-mgmt-probe configure > "$dir/bt-configure.txt"
/tmp/k97-bt-mgmt-probe info > "$dir/bt-powered-info.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-check.txt"
cat /sys/kernel/debug/dri/1/encoder-0/status > "$dir/display-after.txt"
dmesg > "$dir/dmesg-after.txt"
echo AUTO_ADDRESS_BOOT_AND_TWO_GHZ_PASS
