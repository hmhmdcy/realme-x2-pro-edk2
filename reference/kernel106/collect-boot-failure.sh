#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#105 SMP PREEMPT'
mpss=$(/usr/sbin/samurai-modem-remoteproc)
dir=/tmp/k106-first-boot-failure
test ! -e "$dir"
mkdir -m700 "$dir"
{
    uname -a
    cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted
    cat $mpss/state
    ls /sys/class/drm /sys/class/graphics
} > "$dir/state.txt"
dmesg > "$dir/dmesg.txt"
cp /run/samurai-wifi-boot.log /run/samurai-bluetooth-boot.log "$dir/"
cp /run/samurai-wifi/boot-finished "$dir/"
cp -a /run/samurai-radio-address "$dir/"
cat "$(/tmp/k106-haptics-device)/status" > "$dir/haptics-status.txt"
cat /proc/modules > "$dir/modules.txt"
cat /proc/mounts > "$dir/mounts.txt"
cat /proc/interrupts > "$dir/interrupts.txt"
ps > "$dir/processes.txt"
qrtr-lookup > "$dir/qrtr.txt"
for name in wpa.log tftp.log rmtfs.log nv-source-hashes.txt nv-snapshot-sha256.txt firmware-check.txt; do
    test ! -f "/run/samurai-wifi/$name" || cp "/run/samurai-wifi/$name" "$dir/"
done
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-source-check.txt"
sha256sum /usr/sbin/samurai-wifi > "$dir/service-hash.txt"
for file in /sys/fs/pstore/*; do test -f "$file" || continue; cp "$file" "$dir/"; done
(cd "$dir" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k106-first-boot-failure.tar k106-first-boot-failure
sha256sum /tmp/k106-first-boot-failure.tar
