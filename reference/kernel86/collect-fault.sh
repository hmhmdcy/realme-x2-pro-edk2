#!/bin/sh
# Preserve the triggered snapshot and later state; never clear or rearm here.
set -eu
prefix=/tmp/k86-fault
trace=/sys/kernel/tracing/instances/display
[ ! -e "$prefix.tar.gz" ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = 32bf2d8f-8dde-47dc-9b88-e87db9e95198 ]
[ "$(cat "$trace/tracing_on")" = 0 ]
[ ! -e /sys/bus/i2c/devices/0-005c ]
{
    cat /proc/sys/kernel/random/boot_id
    uname -a
    cat /proc/uptime
    cat /proc/sys/kernel/tainted
    cat /sys/class/power_supply/bq28z610-0/uevent
    cat /sys/kernel/debug/dri/1/encoder-0/status
    cat "$trace/events/dpu/dpu_enc_frame_done_timeout/trigger"
    cat "$trace/tracing_on"
    ls /sys/bus/i2c/devices
} >"$prefix-state.txt"
cat "$trace/trace" >"$prefix-trace.txt"
cat "$trace/snapshot" >"$prefix-snapshot.txt"
for cpu in "$trace"/per_cpu/cpu*; do echo "$cpu"; cat "$cpu/stats"; done >"$prefix-trace-stats.txt"
{
    cat "$trace/current_tracer"
    cat "$trace/trace_clock"
    cat "$trace/buffer_size_kb"
    cat "$trace/tracing_on"
    cat "$trace/events/dpu/dpu_enc_frame_done_timeout/trigger"
} >"$prefix-trace-settings.txt"
cat /sys/kernel/debug/dri/1/state >"$prefix-drm-state.txt"
cat /sys/kernel/debug/dri/1/kms >"$prefix-kms.txt"
cat /sys/kernel/debug/clk/clk_summary >"$prefix-clocks.txt"
[ "$(sha256sum /tmp/k86-read-mp2650 | cut -d ' ' -f1)" = 6ef5467f5a445d718bd783ed86aabe5e93d08c442f483978355ad42ec79d5673 ]
/tmp/k86-read-mp2650 /dev/i2c-0 >"$prefix-registers.txt"
{
    head -c 6682624 /dev/sde11 | sha256sum
    sha256sum /dev/sde32
} >"$prefix-partition-hashes.txt"
dmesg >"$prefix-dmesg.txt"
sha256sum "$prefix"-*.txt >"$prefix-hashes.txt"
tar -cf "$prefix.tar" "$prefix"-*.txt
gzip -c "$prefix.tar" >"$prefix.tar.gz"
cat "$prefix-state.txt"
sha256sum "$prefix.tar.gz"
