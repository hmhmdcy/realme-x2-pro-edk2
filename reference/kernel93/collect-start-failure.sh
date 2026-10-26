#!/bin/sh
set -eu
umask 077
dir=/tmp/k93-start-failure
test ! -e "$dir"
mkdir -m 700 "$dir"
dmesg > "$dir/dmesg.txt"
{
    uname -a
    cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted
    cat /sys/class/remoteproc/remoteproc0/state /sys/class/remoteproc/remoteproc0/coredump
} > "$dir/state.txt"
cp /proc/interrupts "$dir/interrupts.txt"
/usr/sbin/qrtr-lookup > "$dir/qrtr.txt"
cp /run/samurai-wifi-boot.log "$dir/"
for name in tftp.log rmtfs.log nv-source-hashes.txt nv-snapshot-sha256.txt; do cp "/run/samurai-wifi/$name" "$dir/"; done
for file in /tmp/k93-bt-*.txt /tmp/k93-nfc-controller.txt; do cp "$file" "$dir/"; done
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-check.txt"
(cd "$dir" && sha256sum * > SHA256SUMS)
tar -C /tmp -cf /tmp/k93-start-failure.tar k93-start-failure
sha256sum /tmp/k93-start-failure.tar
