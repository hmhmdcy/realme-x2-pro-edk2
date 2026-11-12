#!/bin/sh
#
# Capture read-only Type-C/USB/suspend evidence from a running samurai device.
# Usage: sh capture-typec-evidence.sh OUTPUT_FILE
#
set -u

OUT=${1:?usage: capture-typec-evidence.sh OUTPUT_FILE}

mkdir -p "$(dirname "$OUT")"

{
	echo "=== date ==="
	date -Is
	echo "=== boot ==="
	cat /proc/sys/kernel/random/boot_id
	uname -a
	echo "=== typec tree ==="
	for port in /sys/class/typec/port*; do
		[ -e "$port" ] || continue
		echo "-- $port"
		for file in "$port"/*; do
			[ -e "$file" ] || continue
			printf '%s=' "$file"
			cat "$file" 2>/dev/null | tr '\n' ' ' || true
			echo
		done
	done
	echo "=== power ==="
	for supply in mp2650-input mp2650-battery samurai-usb-input; do
		for attr in online status voltage_now current_now usb_type; do
			file="/sys/class/power_supply/$supply/$attr"
			[ -e "$file" ] || continue
			printf '%s=' "$file"
			cat "$file" 2>/dev/null || true
		done
	done
	echo "=== udc ==="
	for file in state current_speed maximum_speed; do
		printf '%s=' "$file"
		cat "/sys/class/udc/a600000.usb/$file" 2>/dev/null || true
	done
	echo "=== net ==="
	ip -br link show usb0 2>/dev/null || true
	cat /sys/class/net/usb0/carrier 2>/dev/null || true
	echo "=== mem_sleep ==="
	cat /sys/power/mem_sleep
	echo "=== suspend_stats ==="
	for file in /sys/power/suspend_stats/*; do
		printf '%s=' "$file"
		cat "$file" 2>/dev/null | tr '\n' ' ' || true
		echo
	done
	echo "=== interrupts ==="
	grep -Ei 'pmic|typec|spmi|pdc|usb|dwc3' /proc/interrupts || true
	echo "=== wakeup_sources ==="
	cat /sys/kernel/debug/wakeup_sources 2>/dev/null |
		grep -Ei 'typec|pmic|usb|wlan|rtc|qpnp' || true
	echo "=== dmesg ==="
	dmesg | grep -Ei 'typec|tcpm|pmic-typec|pdphy|hard-reset|dwc3|usb' |
		tail -n 160 || true
	echo "=== modules ==="
	lsmod | grep -E 'samurai|qcom_pmic|dtbo' || true
	echo "=== services ==="
	rc-service samurai-usb status 2>&1 || true
	rc-service samurai-usb-recover status 2>&1 || true
} >"$OUT" 2>&1

wc -l "$OUT"
