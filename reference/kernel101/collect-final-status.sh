#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#100 SMP PREEMPT'
dir=/tmp/k101-final-status
test ! -e "$dir"
mkdir -m700 "$dir"
mpss=$(/usr/sbin/samurai-modem-remoteproc)
adsp=$(cat /tmp/k101-audio-runtime/adsp-path.txt)
{
    uname -a
    cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted
    cat "$mpss/state" "$adsp/state"
} > "$dir/state.txt"
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/wifi-status.txt"
/tmp/k101-bt-mgmt-probe info > "$dir/bt-info.txt"
cat /sys/bus/aprbus/devices/*/samurai_api > "$dir/native-api.txt"
cat /sys/bus/i2c/devices/1-005a/status > "$dir/haptics-status.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-check.txt"
sha256sum /dev/sda2 > "$dir/persist.sha"
dmesg > "$dir/dmesg.txt"
(cd "$dir" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k101-final-status.tar k101-final-status
sha256sum /tmp/k101-final-status.tar
