#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#98 SMP PREEMPT'
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline ]
grep -qx 1 /run/samurai-wifi/boot-finished
test ! -e /run/samurai-wifi/ready
test -d /run/samurai-wifi/nv
[ -z "$(ls -A /run/samurai-wifi/nv)" ]
test ! -e /tmp/k99-first-wifi-state
dir=/tmp/k99-radio-ram-recovery
test ! -e "$dir"
mkdir -m700 "$dir"
ps > "$dir/processes-before.txt"
test ! -e /run/samurai-bluetooth/lifecycle.lock
cp /usr/sbin/samurai-wifi "$dir/service-before"
sha256sum /usr/sbin/samurai-wifi /tmp/k99-samurai-wifi > "$dir/service-hashes.txt"
mv /run/samurai-wifi /tmp/k99-first-wifi-state
mkdir -m700 /run/samurai-wifi
touch /run/samurai-wifi/boot-started
cp /tmp/k99-samurai-wifi /usr/sbin/samurai-wifi
chmod 755 /usr/sbin/samurai-wifi
result=0
/usr/sbin/samurai-wifi start > "$dir/wifi-start.txt" 2>&1 || result=$?
printf '%s\n' "$result" > /run/samurai-wifi/boot-finished.tmp
mv /run/samurai-wifi/boot-finished.tmp /run/samurai-wifi/boot-finished
printf '%s\n' "$result" > "$dir/wifi-result.txt"
[ "$result" = 0 ]
/usr/sbin/samurai-bluetooth start > "$dir/bt-start.txt" 2>&1
/usr/sbin/samurai-radio-address status > "$dir/address-status.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-check.txt"
dmesg > "$dir/dmesg-after.txt"
{
    cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted
    cat /sys/class/remoteproc/remoteproc0/state
    cat /sys/kernel/debug/dri/1/encoder-0/status
} > "$dir/state.txt"
echo RADIO_RAM_RECOVERY_PASS > "$dir/result.txt"
(cd "$dir" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k99-radio-ram-recovery.tar k99-radio-ram-recovery
sha256sum /tmp/k99-radio-ram-recovery.tar
