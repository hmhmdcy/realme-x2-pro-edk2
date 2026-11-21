#!/bin/sh
set -u

SECONDS_TO_SLEEP=${1:-20}
LOG=/root/typec-suspend-control.log

count_irqs() {
	awk '
		/cc-state-change|vbus-change|attach-detach|samurai-pmic-typec/ {
			print
		}
	' /proc/interrupts
}

snapshot() {
	label=$1
	echo "SNAPSHOT=${label}"
	date -Is
	cat /proc/uptime
	cat /proc/sys/kernel/random/boot_id
	cat /proc/sys/kernel/tainted
	cat /sys/power/mem_sleep
	cat /sys/power/suspend_stats/success
	cat /sys/power/suspend_stats/fail
	cat /sys/class/udc/a600000.usb/state
	cat /sys/class/power_supply/mp2650-input/online
	cat /sys/class/typec/port0/power_role 2>/dev/null
	cat /sys/class/typec/port0/data_role 2>/dev/null
	cat /sys/class/typec/port0/orientation 2>/dev/null
	cat /sys/bus/platform/devices/samurai-pmic-typec.*/power/wakeup 2>/dev/null
	grep -E 'samurai-pmic-typec|qcom_pmic|typec' /sys/power/wakeup_sources
	count_irqs
}

{
	snapshot before
	echo "RTC_WAKEALARM=$(cat /sys/class/rtc/rtc0/wakealarm 2>/dev/null)"
	rtcwake -m mem -s "${SECONDS_TO_SLEEP}"
	echo "RTCWAKE_RC=$?"
	snapshot after
	dmesg | tail -n 180
} >"${LOG}" 2>&1

cat "${LOG}"
