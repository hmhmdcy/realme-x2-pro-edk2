#!/bin/sh
# Capture trace events around one short rtcwake cycle.
set -u

DURATION=${1:-5}
OUT=${2:-/root/suspend-trace-$DURATION.log}
TRACE=${TRACE_ROOT:-/sys/kernel/debug/tracing}

{
	echo "start=$(date -Is)"
	echo "boot_id=$(cat /proc/sys/kernel/random/boot_id)"
	echo "suspend_success_before=$(cat /sys/power/suspend_stats/success)"
	echo "uptime_before=$(cat /proc/uptime)"
	echo "typec_wakeup=$(cat /sys/bus/platform/devices/c440000.spmi:pmic@2:typec@1500/power/wakeup 2>/dev/null)"

	echo 0 >"$TRACE/tracing_on"
	echo >"$TRACE/trace"
	echo 32768 >"$TRACE/buffer_size_kb"
	echo 1 >"$TRACE/events/power/suspend_resume/enable"
	echo 1 >"$TRACE/events/power/wakeup_source_activate/enable"
	echo 1 >"$TRACE/events/power/wakeup_source_deactivate/enable"
	echo 1 >"$TRACE/events/irq/irq_handler_entry/enable"
	echo 1 >"$TRACE/events/irq/irq_handler_exit/enable"
	echo 1 >"$TRACE/events/timer/timer_start/enable"
	echo 1 >"$TRACE/tracing_on"

	rtcwake -m mem -s "$DURATION"
	rc=$?

	echo 0 >"$TRACE/tracing_on"
	echo "rtcwake_rc=$rc"
	echo "end=$(date -Is)"
	echo "uptime_after=$(cat /proc/uptime)"
	echo "suspend_success_after=$(cat /sys/power/suspend_stats/success)"
	echo "=== WAKE SOURCES ==="
	cat /sys/kernel/debug/wakeup_sources
	echo "=== DMESG ==="
	dmesg | grep -E 'PM: suspend|dwc3-qcom|typec|wakeup|rtc' | tail -60
	echo "=== TRACE ==="
	cat "$TRACE/trace"
} >"$OUT" 2>&1

echo "$OUT"
tail -n 80 "$OUT"
