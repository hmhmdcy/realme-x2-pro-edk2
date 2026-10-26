#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#105 SMP PREEMPT'
for attempt in $(seq 1 45); do
    test ! -f /run/samurai-wifi/boot-finished || break
    sleep 1
done
test -f /run/samurai-wifi/boot-finished
awk '{if ($1 < 100) exit 1}' /proc/uptime
radio=/sys/kernel/tracing/instances/radio
mountpoint -q /sys/kernel/tracing || mount -t tracefs tracefs /sys/kernel/tracing
test -d "$radio"
test "$(cat "$radio/events/qrtr/enable")" = 1
test "$(cat "$radio/events/qcom_glink/enable")" = 1
test "$(cat "$radio/events/samurai_diag/enable")" = 1
dir=/tmp/k106-first-radio-trace
test ! -e "$dir"
mkdir -m700 "$dir"
echo 0 > "$radio/tracing_on"
cat "$radio/trace" > "$dir/trace.txt"
for cpu in "$radio"/per_cpu/cpu*; do
    cat "$cpu/stats" > "$dir/${cpu##*/}-stats.txt"
done
cat /proc/bootconfig > "$dir/bootconfig.txt"
cat "$radio/trace_clock" "$radio/buffer_size_kb" "$radio/tracing_on" > "$dir/settings.txt"
cat /sys/kernel/tracing/instances/display/trace_clock /sys/kernel/tracing/instances/display/buffer_size_kb > "$dir/display-settings.txt"
{
    uname -a
    cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted
    for p in /sys/class/remoteproc/remoteproc*; do cat "$p/name" "$p/state"; done
} > "$dir/state.txt"
dmesg > "$dir/dmesg.txt"
qrtr-lookup > "$dir/qrtr.txt"
ps > "$dir/processes.txt"
cp /run/samurai-wifi/boot-finished /run/samurai-wifi-boot.log /run/samurai-bluetooth-boot.log "$dir/"
for n in tftp.log rmtfs.log firmware-check.txt nv-source-hashes.txt; do cp "/run/samurai-wifi/$n" "$dir/$n"; done
cat /run/samurai-wifi/tftp.pid /run/samurai-wifi/rmtfs.pid > "$dir/server-pids.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-check.txt"
(cd "$dir" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k106-first-radio-trace.tar k106-first-radio-trace
sha256sum /tmp/k106-first-radio-trace.tar
echo FIRST_AUTOMATIC_RADIO_TRACE_CAPTURED
