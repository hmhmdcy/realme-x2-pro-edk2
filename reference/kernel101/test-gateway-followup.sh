#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#100 SMP PREEMPT'
dir=/tmp/k101-gateway-followup
test ! -e "$dir"
mkdir -m700 "$dir"
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/status-before.txt"
grep -qx wpa_state=COMPLETED "$dir/status-before.txt"
grep -qx freq=5180 "$dir/status-before.txt"
gateway=$(sed -n 's/^router=//p' /run/samurai-wifi/dhcp-lease.txt | awk '{print $1}')
test -n "$gateway"
ping -I wlan0 -c5 -W3 "$gateway" > "$dir/gateway.txt" 2>&1
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/status-after.txt"
cp /run/samurai-wifi/wpa.log "$dir/"
dmesg > "$dir/dmesg.txt"
{
    cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted
    for p in /sys/class/remoteproc/remoteproc*; do cat "$p/name" "$p/state"; done
} > "$dir/state.txt"
(cd "$dir" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k101-gateway-followup.tar k101-gateway-followup
sha256sum /tmp/k101-gateway-followup.tar
