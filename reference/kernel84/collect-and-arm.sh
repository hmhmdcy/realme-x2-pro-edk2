#!/bin/sh
# Preserve final observations and arm only the bounded display trace instance.
set -eu
prefix=/tmp/k84-final
trace=/sys/kernel/tracing/instances/display
[ ! -e "$prefix.tar" ]
[ -r /tmp/k84-probe-large-hashes.txt ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = f02d218a-cc7d-4b92-8858-c8eeaeab5777 ]
uname -a | grep -q '#85 SMP PREEMPT'
[ "$(sha256sum /tmp/k84-read-mp2650 | cut -d ' ' -f1)" = 6ef5467f5a445d718bd783ed86aabe5e93d08c442f483978355ad42ec79d5673 ]
[ "$(readlink -f /sys/bus/i2c/devices/i2c-0/of_node)" = /sys/firmware/devicetree/base/soc@0/geniqup@8c0000/i2c@884000 ]
grep -qx 'PARTNAME=boot' /sys/class/block/sde11/uevent
grep -qx 'PARTNAME=logdump' /sys/class/block/sde32/uevent
[ "$(cat /sys/class/block/sde11/size)" = 196608 ]
[ "$(cat /sys/class/block/sde32/size)" = 131072 ]
{
    cat /proc/sys/kernel/random/boot_id
    uname -a
    cat /proc/uptime
    cat /proc/sys/kernel/tainted
    cat /sys/class/power_supply/bq28z610-0/uevent
    cat /sys/kernel/debug/dri/1/encoder-0/status
    cat /proc/modules
    cat /sys/class/block/sde11/uevent
    cat /sys/class/block/sde32/uevent
} >"$prefix-state.txt"
/tmp/k84-read-mp2650 /dev/i2c-0 >"$prefix-registers.txt"
cat /sys/kernel/debug/dri/1/state >"$prefix-drm-state.txt"
cat /sys/kernel/debug/dri/1/kms >"$prefix-kms.txt"
cat /sys/kernel/debug/clk/clk_summary >"$prefix-clocks.txt"
{
    head -c 6682624 /dev/sde11 | sha256sum
    sha256sum /dev/sde32
} >"$prefix-partition-hashes.txt"
grep -q '^08edf9bcc1c55977169b0a8fd9f963805ba98d0423929e09e17bb9f811ca7405 ' "$prefix-partition-hashes.txt"
grep -q '^60e183a6780945885a738ac1bd0c7e23ed41515bca662cb50a831ede3b57302b ' "$prefix-partition-hashes.txt"
dmesg >"$prefix-dmesg.txt"
grep -q 'frame_done_cnt:0mode:' "$prefix-state.txt"
grep -qx 'snapshot:count=1' "$trace/events/dpu/dpu_enc_frame_done_timeout/trigger"
[ "$(cat "$trace/tracing_on")" = 0 ]
[ "$(cat "$trace/buffer_size_kb")" = 2051 ]
# The previous two traces and snapshots were captured before this buffer clear.
echo 0 >"$trace/trace"
echo 1 >"$trace/tracing_on"
echo 'k84 idle monitoring begin' >"$trace/trace_marker"
{
    cat "$trace/current_tracer"
    cat "$trace/trace_clock"
    cat "$trace/buffer_size_kb"
    cat "$trace/tracing_on"
    cat "$trace/events/dpu/dpu_enc_frame_done_timeout/trigger"
    cat "$trace/set_event"
} >"$prefix-monitor-settings.txt"
sha256sum "$prefix-state.txt" "$prefix-registers.txt" "$prefix-drm-state.txt" "$prefix-kms.txt" "$prefix-clocks.txt" "$prefix-partition-hashes.txt" "$prefix-dmesg.txt" "$prefix-monitor-settings.txt" >"$prefix-hashes.txt"
tar -cf "$prefix.tar" "$prefix-state.txt" "$prefix-registers.txt" "$prefix-drm-state.txt" "$prefix-kms.txt" "$prefix-clocks.txt" "$prefix-partition-hashes.txt" "$prefix-dmesg.txt" "$prefix-monitor-settings.txt" "$prefix-hashes.txt"
gzip -c "$prefix.tar" >"$prefix.tar.gz"
cat "$prefix-state.txt"
cat "$prefix-registers.txt"
sha256sum "$prefix.tar" "$prefix.tar.gz"
