#!/bin/sh
set -eu
prefix=/tmp/k84-probe
trace=/sys/kernel/tracing/instances/display
[ ! -e "$prefix.tar" ]
uname -a | grep -q '#85 SMP PREEMPT'
[ -r /tmp/k84-ready-trace.txt ]
[ "$(sha256sum /tmp/k84-kms-pageflip | cut -d ' ' -f1)" = 7abbfa366bc688b50379f2fee65f54510b7805d0c498f7930e0f4531b96cd42b ]
! pidof k84-kms-pageflip
cat /sys/kernel/debug/dri/1/encoder-0/status >"$prefix-before-encoder.txt"
dmesg >"$prefix-before-dmesg.txt"
# The initial trace/snapshot are already preserved by collect-initial.sh.
# The timeout snapshot action retains its current count; it is not re-armed here.
echo 0 >"$trace/trace"
echo 1 >"$trace/tracing_on"
echo 'k84 pageflip begin' >"$trace/trace_marker"
set +e
( cat /proc/uptime; /tmp/k84-kms-pageflip /dev/dri/card1 0; code=$?; echo "tool_rc=$code"; cat /proc/uptime; exit "$code" ) >"$prefix-pageflip.txt" 2>&1
tool_code=$?
set -e
echo 'k84 pageflip returned' >"$trace/trace_marker"
# Keep tracing across direct console restoration and the ensuing idle interval.
sleep 5
echo 'k84 idle observation end' >"$trace/trace_marker"
echo 0 >"$trace/tracing_on"
cat "$trace/trace" >"$prefix-trace.txt"
cat "$trace/snapshot" >"$prefix-snapshot.txt"
cat "$trace/events/dpu/dpu_enc_frame_done_timeout/trigger" >"$prefix-trigger.txt"
for cpu in "$trace"/per_cpu/cpu*; do echo "$cpu"; cat "$cpu/stats"; done >"$prefix-trace-stats.txt"
cat /sys/kernel/debug/dri/1/encoder-0/status >"$prefix-after-encoder.txt"
cat /sys/kernel/debug/dri/1/state >"$prefix-drm-state.txt"
cat /sys/kernel/debug/dri/1/kms >"$prefix-kms.txt"
cat /sys/kernel/debug/clk/clk_summary >"$prefix-clocks.txt"
cat /sys/class/power_supply/bq28z610-0/uevent >"$prefix-battery.txt"
dmesg >"$prefix-after-dmesg.txt"
sha256sum "$prefix-before-encoder.txt" "$prefix-before-dmesg.txt" "$prefix-pageflip.txt" "$prefix-trace.txt" "$prefix-snapshot.txt" "$prefix-trigger.txt" "$prefix-trace-stats.txt" "$prefix-after-encoder.txt" "$prefix-drm-state.txt" "$prefix-kms.txt" "$prefix-clocks.txt" "$prefix-battery.txt" "$prefix-after-dmesg.txt" >"$prefix-hashes.txt"
tar -cf "$prefix.tar" "$prefix-before-encoder.txt" "$prefix-before-dmesg.txt" "$prefix-pageflip.txt" "$prefix-trace.txt" "$prefix-snapshot.txt" "$prefix-trigger.txt" "$prefix-trace-stats.txt" "$prefix-after-encoder.txt" "$prefix-drm-state.txt" "$prefix-kms.txt" "$prefix-clocks.txt" "$prefix-battery.txt" "$prefix-after-dmesg.txt" "$prefix-hashes.txt"
cat "$prefix-after-encoder.txt"
tail -n 6 "$prefix-pageflip.txt"
exit "$tool_code"
