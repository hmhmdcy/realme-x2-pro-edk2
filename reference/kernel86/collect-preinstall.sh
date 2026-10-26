#!/bin/sh
# Stop only the diagnostic trace instance after preserving the first boot.
set -eu
prefix=/tmp/k86-preinstall
[ ! -e "$prefix.tar" ]
uname -a | grep -q '#85 SMP PREEMPT'
[ "$(cat /proc/sys/kernel/random/boot_id)" = f02d218a-cc7d-4b92-8858-c8eeaeab5777 ]
grep -q ' /sys/kernel/debug debugfs ' /proc/mounts || mount -t debugfs debugfs /sys/kernel/debug
grep -q ' /sys/kernel/tracing tracefs ' /proc/mounts || mount -t tracefs tracefs /sys/kernel/tracing
trace=/sys/kernel/tracing/instances/display
[ -d "$trace" ]
{
    cat /proc/sys/kernel/random/boot_id
    uname -a
    cat /proc/uptime
    cat /proc/sys/kernel/tainted
    cat /proc/cmdline
    cat /proc/bootconfig
    cat /sys/class/power_supply/bq28z610-0/uevent
    cat /sys/kernel/debug/dri/1/encoder-0/status
    cat /proc/modules
} >"$prefix-state.txt" 2>&1
{
    cat "$trace/current_tracer"
    cat "$trace/trace_clock"
    cat "$trace/buffer_size_kb"
    cat "$trace/tracing_on"
    cat "$trace/events/dpu/dpu_enc_frame_done_timeout/trigger"
    cat "$trace/set_event"
} >"$prefix-trace-settings.txt"
echo 0 >"$trace/tracing_on"
cat "$trace/trace" >"$prefix-trace.txt"
cat "$trace/snapshot" >"$prefix-snapshot.txt"
for cpu in "$trace"/per_cpu/cpu*; do
    echo "$cpu"; cat "$cpu/stats"
done >"$prefix-trace-stats.txt"
cat /sys/kernel/debug/dri/1/state >"$prefix-drm-state.txt"
cat /sys/kernel/debug/dri/1/kms >"$prefix-kms.txt"
cat /sys/kernel/debug/clk/clk_summary >"$prefix-clocks.txt"
zcat /proc/config.gz >"$prefix-config.txt"
grep -qx 'PARTNAME=boot' /sys/class/block/sde11/uevent
grep -qx 'PARTNAME=logdump' /sys/class/block/sde32/uevent
{
    head -c 6682624 /dev/sde11 | sha256sum
    sha256sum /dev/sde32
} >"$prefix-partition-hashes.txt"
dmesg >"$prefix-dmesg.txt"
sha256sum "$prefix-state.txt" "$prefix-trace-settings.txt" "$prefix-trace.txt" "$prefix-snapshot.txt" "$prefix-trace-stats.txt" "$prefix-drm-state.txt" "$prefix-kms.txt" "$prefix-clocks.txt" "$prefix-config.txt" "$prefix-partition-hashes.txt" "$prefix-dmesg.txt" >"$prefix-hashes.txt"
/tmp/k84-read-mp2650 /dev/i2c-0 >"$prefix-registers.txt"
sha256sum "$prefix-registers.txt" >>"$prefix-hashes.txt"
tar -cf "$prefix.tar" "$prefix-registers.txt" "$prefix-state.txt" "$prefix-trace-settings.txt" "$prefix-trace.txt" "$prefix-snapshot.txt" "$prefix-trace-stats.txt" "$prefix-drm-state.txt" "$prefix-kms.txt" "$prefix-clocks.txt" "$prefix-config.txt" "$prefix-partition-hashes.txt" "$prefix-dmesg.txt" "$prefix-hashes.txt"
cat "$prefix-state.txt"
cat "$prefix-trace-settings.txt" | head -n 7
cat "$prefix-partition-hashes.txt"
gzip -c "$prefix.tar" >"$prefix.tar.gz"
