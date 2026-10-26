#!/bin/sh
set -eu
umask 077
[ "$#" = 3 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
case "$2:$3" in 2462:two-ghz-data|5180:final-five-ghz) frequency=$2;phase=$3;; *) exit 2;; esac
dir=/tmp/k98-$phase
test ! -e "$dir"
mkdir -m700 "$dir"
cli() { /usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 "$@"; }
cli set_network 0 freq_list "$frequency" | grep -qx OK
cli reassociate | grep -qx OK
for attempt in $(seq 1 30); do
    cli status > "$dir/status.txt"
    if grep -qx wpa_state=COMPLETED "$dir/status.txt" && grep -qx "freq=$frequency" "$dir/status.txt"; then break; fi
    sleep 2
done
grep -qx wpa_state=COMPLETED "$dir/status.txt"
grep -qx "freq=$frequency" "$dir/status.txt"
udhcpc -i wlan0 -s /usr/sbin/samurai-udhcpc-wlan -n -q -t 5 -T 3 > "$dir/dhcp.txt" 2>&1
echo BAND_AUTH_DHCP_PASS
