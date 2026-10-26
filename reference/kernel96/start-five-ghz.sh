#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
grep -qx HOT_CYCLE_RECOVERY_PASS /tmp/k96-hot-cycle.log
grep -qx COEXISTENCE_OBSERVATION_PASS /tmp/k96-recovery-coexistence.log
dir=/tmp/k96-five-ghz
test ! -e "$dir"
mkdir -m 700 "$dir"
cli() { /usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 "$@"; }
cli status > "$dir/status-before.txt"
grep -qx wpa_state=COMPLETED "$dir/status-before.txt"
cli set_network 0 freq_list 5180 | grep -qx OK
cli select_network 0 | grep -qx OK
cli reassociate | grep -qx OK
for attempt in $(seq 1 20); do
    cli status > "$dir/status-after.txt"
    if grep -qx wpa_state=COMPLETED "$dir/status-after.txt" && grep -qx freq=5180 "$dir/status-after.txt"; then break; fi
    sleep 3
done
grep -qx wpa_state=COMPLETED "$dir/status-after.txt"
grep -qx freq=5180 "$dir/status-after.txt"
udhcpc -i wlan0 -s /usr/sbin/samurai-udhcpc-wlan -n -q -t 5 -T 3 > "$dir/dhcp.txt" 2>&1
dmesg > "$dir/dmesg-after.txt"
echo FIVE_GHZ_AUTH_DHCP_PASS
