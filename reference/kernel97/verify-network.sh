#!/bin/sh
set -eu
umask 077
[ "$#" = 3 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
case "$2" in initial|initial-retry1|recovery|five-ghz|five-ghz-retry1) phase=$2;; *) exit 2;; esac
case "$3" in 2462|5180) frequency=$3;; *) exit 2;; esac
dir=/tmp/k97-$phase-network
test ! -e "$dir"
mkdir -m 700 "$dir"
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/status.txt"
grep -qx wpa_state=COMPLETED "$dir/status.txt"
grep -qx "freq=$frequency" "$dir/status.txt"
gateway=$(sed -n 's/^router=//p' /run/samurai-wifi/dhcp-lease.txt | awk '{print $1}')
test -n "$gateway"
ip route get 1.1.1.1 > "$dir/route.txt"
grep -q 'dev wlan0' "$dir/route.txt"
ping -I wlan0 -c 3 -W 3 "$gateway" > "$dir/gateway.txt" 2>&1
echo GATEWAY_PING=PASS
if ping -I wlan0 -c 3 -W 3 1.1.1.1 > "$dir/internet-ping.txt" 2>&1; then
    echo INTERNET_PING=PASS
else
    echo INTERNET_PING=FAIL
fi
timeout 15 nslookup kernel.org > "$dir/dns.txt" 2>&1
echo DNS_LOOKUP=PASS
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY all_proxy
timeout 20 wget -O "$dir/http.txt" http://example.com/ > "$dir/http.log" 2>&1
echo HTTP_FETCH=PASS
wc -c < "$dir/http.txt"
sha256sum "$dir/http.txt"
[ "$(cat /proc/sys/kernel/tainted)" = 0 ]
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = running ]
echo NETWORK_OBSERVATION_PASS
