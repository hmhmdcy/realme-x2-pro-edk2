#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
dir=/tmp/k97-wifi-only
test ! -e "$dir"
mkdir -m700 "$dir"
/usr/sbin/samurai-radio-address bt > "$dir/bt-address-status.txt"
grep -q 'powered=0 connectable=0 bondable=0' "$dir/bt-address-status.txt"
cat /sys/kernel/debug/dri/1/encoder-0/status > "$dir/display-before.txt"
for attempt in $(seq 1 45); do
    wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/wpa-current.txt"
    grep -qx wpa_state=COMPLETED "$dir/wpa-current.txt"
    grep -qx freq=2462 "$dir/wpa-current.txt"
    [ "$(cat /sys/class/remoteproc/remoteproc0/state)" = running ]
    [ "$(cat /proc/sys/kernel/tainted)" = 0 ]
    printf 'sample=%s uptime=%s BT=off WPA=COMPLETED MPSS=running taint=0\n' "$attempt" "$(cut -d ' ' -f1 /proc/uptime)"
    sleep 2
done
cat /sys/kernel/debug/dri/1/encoder-0/status > "$dir/display-after.txt"
dmesg > "$dir/dmesg-after.txt"
cp /run/samurai-wifi/wpa.log "$dir/wpa.log"
echo WIFI_ONLY_OBSERVATION_PASS
