#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#101 SMP PREEMPT'
dir=/tmp/k102-final-status
test ! -e "$dir"
mkdir -m700 "$dir"
{
    uname -a
    cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted
    for p in /sys/class/remoteproc/remoteproc*; do cat "$p/name" "$p/state"; done
} > "$dir/state.txt"
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/wifi-status.txt"
ls -A /sys/class/bluetooth > "$dir/bt-class.txt"
cat "$(/tmp/k102-haptics-device)/status" > "$dir/haptics-status.txt"
cat /sys/kernel/debug/gpio > "$dir/gpio.txt"
cat /sys/kernel/debug/asoc/components > "$dir/components.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-check.txt"
sha256sum /dev/sda2 > "$dir/persist.sha"
dmesg > "$dir/dmesg.txt"
(cd "$dir" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k102-final-status.tar k102-final-status
sha256sum /tmp/k102-final-status.tar
