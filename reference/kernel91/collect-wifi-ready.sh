#!/bin/sh
set -eu
[ "$(cat /proc/sys/kernel/random/boot_id)" = dfe8e722-f6b7-4ce8-85cc-17dfba80f69d ]
[ ! -e /tmp/k91-wifi-ready.tar ]
dir=/tmp/k91-wifi-ready
mkdir -m 700 "$dir"
dmesg > "$dir/dmesg.txt"
{
    uname -a
    cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted
    cat /sys/class/remoteproc/remoteproc0/state /sys/class/remoteproc/remoteproc0/recovery
    ip link show wlan0
    cat /sys/class/power_supply/bq27541-0/capacity 2>/dev/null || true
} > "$dir/state.txt"
/tmp/k91-qrtr-lookup > "$dir/qrtr.txt"
/tmp/k91-iw phy > "$dir/phy.txt"
/tmp/k91-iw reg get > "$dir/reg.txt"
cp /tmp/k91-live-rmtfs.txt /tmp/k91-live-tftp.txt "$dir/"
cp /tmp/k91-scan1.txt /tmp/k91-scan2.txt /tmp/k91-scan3.txt "$dir/"
cp /tmp/k91-scan1.err /tmp/k91-scan2.err /tmp/k91-scan3.err "$dir/"
sha256sum -c /tmp/k91-nv-source-hashes.txt > "$dir/nv-partition-check.txt"
(cd /tmp/k91-nv && sha256sum -c /tmp/k91-nv-SHA256SUMS) > "$dir/nv-snapshot-check.txt"
(cd "$dir" && sha256sum * > SHA256SUMS)
tar -C /tmp -cf /tmp/k91-wifi-ready.tar k91-wifi-ready
sha256sum /tmp/k91-wifi-ready.tar
cat /proc/uptime /proc/sys/kernel/tainted
cat /sys/class/remoteproc/remoteproc0/state
