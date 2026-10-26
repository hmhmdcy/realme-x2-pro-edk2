#!/bin/sh
# No recovery, parameter writes, new I2C queries or partition writes.
set -eu
prefix=/tmp/k85-final
trace=/sys/kernel/tracing/instances/display
[ ! -e "$prefix.tar" ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = f02d218a-cc7d-4b92-8858-c8eeaeab5777 ]
{
    cat /proc/sys/kernel/random/boot_id
    uname -a
    cat /proc/uptime
    cat /proc/sys/kernel/tainted
    cat /sys/class/power_supply/bq28z610-0/uevent
    cat /sys/kernel/debug/dri/1/encoder-0/status
    cat "$trace/tracing_on"
    cat "$trace/events/dpu/dpu_enc_frame_done_timeout/trigger"
} >"$prefix-state.txt"
dmesg >"$prefix-dmesg.txt"
{
    cat "$trace/buffer_size_kb"
    cat "$trace/current_tracer"
    cat "$trace/trace_clock"
    cat "$trace/events/enable"
} >"$prefix-trace-config.txt"
grep -qx 'PARTNAME=boot' /sys/class/block/sde11/uevent
grep -qx 'PARTNAME=logdump' /sys/class/block/sde32/uevent
[ "$(cat /sys/class/block/sde11/size)" = 196608 ]
[ "$(cat /sys/class/block/sde32/size)" = 131072 ]
{
    head -c 6682624 /dev/sde11 | sha256sum
    sha256sum /dev/sde32
} >"$prefix-partition-hashes.txt"
sha256sum "$prefix-state.txt" "$prefix-dmesg.txt" "$prefix-trace-config.txt" "$prefix-partition-hashes.txt" >"$prefix-hashes.txt"
tar -cf "$prefix.tar" "$prefix-state.txt" "$prefix-dmesg.txt" "$prefix-trace-config.txt" "$prefix-partition-hashes.txt" "$prefix-hashes.txt"
gzip -c "$prefix.tar" >"$prefix.tar.gz"
cat "$prefix-state.txt"
cat "$prefix-trace-config.txt"
sha256sum "$prefix.tar" "$prefix.tar.gz"
