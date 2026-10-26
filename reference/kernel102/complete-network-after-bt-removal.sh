#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#101 SMP PREEMPT'
grep -qx 0 /run/samurai-wifi/boot-finished
mpss=$(/usr/sbin/samurai-modem-remoteproc)
[ "$(cat "$mpss/state")" = running ]
source=/tmp/k102-auto-network
dir=/tmp/k102-auto-network-completion
test ! -e "$dir"
test ! -e "$source/result.txt"
grep -qx OK "$source/reconfigure.txt"
grep -qx wpa_state=COMPLETED "$source/status.txt"
grep -qx freq=5180 "$source/status.txt"
grep -q '3 packets transmitted, 3 packets received, 0% packet loss' "$source/gateway.txt"
grep -q 'Example Domain' "$source/http.txt"
[ "$(wc -c < "$source/http.txt")" = 577 ]
[ -z "$(ls -A /sys/class/bluetooth)" ]
test ! -e /sys/bus/platform/drivers/qcom_geni_serial/898000.serial/serdev0/driver
mkdir -m700 "$dir" "$dir/original-network-partial"
cp -a "$source/." "$dir/original-network-partial/"
cp /run/samurai-wifi/wpa.log "$dir/"
{
    uname -a
    cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted
    cat "$mpss/state"
} > "$dir/state.txt"
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/status-current.txt"
grep -qx wpa_state=COMPLETED "$dir/status-current.txt"
grep -qx freq=5180 "$dir/status-current.txt"
ls -A /sys/class/bluetooth > "$dir/bt-class.txt"
echo CONTROLLER_REMOVED_BY_EXPLICIT_BT_STOP_NO_PAIR_OR_CONNECT > "$dir/bt-state.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-check.txt"
cat "$(/tmp/k102-haptics-device)/status" > "$dir/haptics-status.txt"
dmesg > "$dir/dmesg.txt"
[ "$(cat /proc/sys/kernel/tainted)" = 0 ]
echo AUTO_BOOT_5G_AUTH_DHCP_GATEWAY_DNS_HTTP_PASS > "$dir/result.txt"
(cd "$dir" && find . -type f ! -path ./SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k102-auto-network-completion.tar k102-auto-network-completion
sha256sum /tmp/k102-auto-network-completion.tar
