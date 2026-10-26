#!/bin/sh
# Read current state without clearing traces, cycling the panel or starting DSPs.
set -eu
prefix=/tmp/k88-handover
trace=/sys/kernel/tracing/instances/display
[ ! -e "$prefix.tar" ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = 32bf2d8f-8dde-47dc-9b88-e87db9e95198 ]
uname -a | grep -q '#86 SMP PREEMPT'
[ "$(cat "$trace/tracing_on")" = 0 ]
grep -qx 'snapshot:count=0' "$trace/events/dpu/dpu_enc_frame_done_timeout/trigger"
{
    cat /proc/sys/kernel/random/boot_id
    uname -a
    cat /proc/uptime
    cat /proc/sys/kernel/tainted
    cat /sys/kernel/debug/dri/1/encoder-0/status
    cat "$trace/events/dpu/dpu_enc_frame_done_timeout/trigger"
    cat "$trace/tracing_on"
    printf 'NETWORK_INTERFACES\n'
    ls /sys/class/net
    printf 'I2C_CLIENTS\n'
    for client in /sys/bus/i2c/devices/*-00*; do basename "$client"; done
    printf 'REMOTEPROC_CLASS\n'
    if [ -d /sys/class/remoteproc ]; then ls /sys/class/remoteproc; else printf 'absent\n'; fi
    printf 'FIRMWARE_MOUNTS\n'
    if grep -E ' /tmp/k88-modem-ro ' /proc/mounts; then exit 1; fi
} >"$prefix-state.txt"
cat "$trace/snapshot" >"$prefix-snapshot.txt"
cat "$trace/trace" >"$prefix-trace.txt"
cat /sys/kernel/debug/dri/1/state >"$prefix-drm-state.txt"
cat /sys/kernel/debug/dri/1/kms >"$prefix-kms.txt"
dmesg >"$prefix-dmesg.txt"
sha256sum "$prefix-state.txt" "$prefix-snapshot.txt" "$prefix-trace.txt" "$prefix-drm-state.txt" "$prefix-kms.txt" "$prefix-dmesg.txt" >"$prefix-hashes.txt"
tar -cf "$prefix.tar" "$prefix-state.txt" "$prefix-snapshot.txt" "$prefix-trace.txt" "$prefix-drm-state.txt" "$prefix-kms.txt" "$prefix-dmesg.txt" "$prefix-hashes.txt"
cat "$prefix-state.txt"
cat "$prefix-hashes.txt"
