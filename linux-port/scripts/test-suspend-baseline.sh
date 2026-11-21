#!/bin/sh
#
# Measure one rtcwake s2idle cycle without changing persistent state.
# Usage: test-suspend-baseline.sh SECONDS [OUTPUT]
#
# Do not use the difference between the printk timestamps at "PM: suspend
# entry" and "PM: suspend exit" as the sleep duration.  On this s2idle
# path the local printk clock is frozen while suspended.  Use the RTC
# seconds and /proc/uptime for the actual elapsed time.
#
set -u

DURATION=${1:-20}
OUT=${2:-/tmp/suspend-baseline-$(date +%s).log}

snapshot()
{
	date -Is
	echo "epoch=$(date +%s)"
	echo "boot_id=$(cat /proc/sys/kernel/random/boot_id)"
	echo "uptime=$(cut -d' ' -f1 /proc/uptime)"
	echo "rtc_epoch=$(cat /sys/class/rtc/rtc0/since_epoch)"
	echo "udc_state=$(cat /sys/class/udc/a600000.usb/state 2>/dev/null)"
	echo "usb_carrier=$(cat /sys/class/net/usb0/carrier 2>/dev/null)"
	echo "vbus_online=$(cat /sys/class/power_supply/mp2650-input/online 2>/dev/null)"
	echo "rtc_time=$(cat /sys/class/rtc/rtc0/time 2>/dev/null)"
	echo "rtc_epoch=$(cat /sys/class/rtc/rtc0/since_epoch 2>/dev/null)"
	echo "rtc_wakealarm=$(cat /sys/class/rtc/rtc0/wakealarm 2>/dev/null)"
	echo "suspend_success=$(cat /sys/power/suspend_stats/success 2>/dev/null)"
	echo "suspend_fail=$(cat /sys/power/suspend_stats/fail 2>/dev/null)"
	echo "last_failed_dev=$(cat /sys/power/suspend_stats/last_failed_dev 2>/dev/null)"
	echo "last_failed_errno=$(cat /sys/power/suspend_stats/last_failed_errno 2>/dev/null)"
	echo "last_failed_step=$(cat /sys/power/suspend_stats/last_failed_step 2>/dev/null)"
	echo "wakeup_irq=$(cat /sys/power/suspend_stats/pm_wakeup_irq 2>/dev/null)"
	echo "--- wakeup_sources ---"
	cat /sys/kernel/debug/wakeup_sources 2>/dev/null |
		grep -Ei 'typec|pmic|usb|wlan|rtc|qpnp' || true
	echo "--- interrupts ---"
	grep -Ei 'pmic|typec|spmi|pdc|usb|dwc3|rtc' /proc/interrupts || true
}

{
	echo "=== BEFORE ==="
	snapshot
	echo "=== RTCWAKE ${DURATION}s ==="
	before_rtc=$(cat /sys/class/rtc/rtc0/since_epoch)
	before_uptime=$(cut -d' ' -f1 /proc/uptime)
	before_success=$(cat /sys/power/suspend_stats/success)
	start=$(date +%s)
	rtcwake -m mem -s "$DURATION"
	rc=$?
	end=$(date +%s)
	after_rtc=$(cat /sys/class/rtc/rtc0/since_epoch)
	after_uptime=$(cut -d' ' -f1 /proc/uptime)
	after_success=$(cat /sys/power/suspend_stats/success)
	echo "rtcwake_rc=$rc"
	echo "wall_elapsed=$((end - start))"
	echo "rtc_elapsed=$((after_rtc - before_rtc))"
	echo "uptime_elapsed=$(awk -v a="$before_uptime" -v b="$after_uptime" 'BEGIN { printf "%.2f", b - a }')"
	echo "suspend_success=$before_success->$after_success"
	echo "=== AFTER ==="
	snapshot
	echo "=== DMESG ==="
	dmesg | grep -Ei 'PM: suspend|PM: failed|dwc3|usb|rtc|wake' |
		tail -n 100 || true
	echo "=== RESULT ==="
	if [ "$rc" -ne 0 ]; then
		echo "RESULT: ERROR"
	elif [ "$after_success" -le "$before_success" ]; then
		echo "RESULT: NO_SUSPEND"
	elif [ "$((after_rtc - before_rtc))" -ge "$((DURATION - 2))" ]; then
		echo "RESULT: SLEPT"
	else
		echo "RESULT: EARLY_RETURN"
	fi
} >"$OUT" 2>&1

cat "$OUT"
