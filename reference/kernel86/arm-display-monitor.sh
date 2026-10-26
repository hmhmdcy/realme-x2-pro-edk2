#!/bin/sh
set -eu
trace=/sys/kernel/tracing/instances/display
[ "$(cat /proc/sys/kernel/random/boot_id)" = 32bf2d8f-8dde-47dc-9b88-e87db9e95198 ]
[ -s /tmp/k86-initial-hashes.txt ]
sha256sum -c /tmp/k86-initial-hashes.txt >/tmp/k86-initial-hashes-recheck.txt
grep -q 'frame_done_cnt:0mode:' /sys/kernel/debug/dri/1/encoder-0/status
[ "$(cat "$trace/tracing_on")" = 0 ]
grep -qx 'snapshot:count=1' "$trace/events/dpu/dpu_enc_frame_done_timeout/trigger"
# The initial trace and snapshot were copied and audited before resizing/clearing.
echo 2048 >"$trace/buffer_size_kb"
echo 0 >"$trace/trace"
echo 1 >"$trace/tracing_on"
echo 'k86 input observer monitoring begin' >"$trace/trace_marker"
{
    cat "$trace/current_tracer"
    cat "$trace/trace_clock"
    cat "$trace/buffer_size_kb"
    cat "$trace/tracing_on"
    cat "$trace/events/dpu/dpu_enc_frame_done_timeout/trigger"
} >/tmp/k86-monitor-settings.txt
cat /tmp/k86-monitor-settings.txt
