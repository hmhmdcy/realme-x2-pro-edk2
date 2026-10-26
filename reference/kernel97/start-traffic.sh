#!/bin/sh
set -eu
umask 077
[ "$#" = 3 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
case "$2" in initial|initial-retry1|recovery|five-ghz) phase=$2;; *) exit 2;; esac
case "$3" in 2462|5180) frequency=$3;; *) exit 2;; esac
prefix=/tmp/k97-$phase
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$prefix-traffic-wpa.txt"
grep -qx wpa_state=COMPLETED "$prefix-traffic-wpa.txt"
grep -qx "freq=$frequency" "$prefix-traffic-wpa.txt"
test ! -e "$prefix-traffic.bin"
test ! -e "$prefix-traffic-upload.bin"
dd if=/dev/urandom of="$prefix-traffic.bin" bs=1048576 count=4
cp /run/samurai-wifi/dhcp-lease.txt "$prefix-traffic-dhcp.txt"
nohup /tmp/k97-wifi-traffic-server "$(sed -n 's/^ip=//p' /run/samurai-wifi/dhcp-lease.txt)" "$phase" > "$prefix-traffic-server.log" 2>&1 < /dev/null &
echo $! > "$prefix-traffic-server.pid"
for attempt in $(seq 1 5); do
    grep -q WIFI_TRAFFIC_READY "$prefix-traffic-server.log" && break
    sleep 1
done
grep -q WIFI_TRAFFIC_READY "$prefix-traffic-server.log"
echo TRAFFIC_SERVER_READY
