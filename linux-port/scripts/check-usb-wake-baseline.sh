#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
#
# Read-only USB VBUS wake gate for the RMX1931.
# Run after booting the usb2-vbus-wake DTB candidate.

set -u

require_enabled=0
if [ "${1:-}" = "--require-enabled" ]; then
	require_enabled=1
fi

failures=0

fail()
{
	echo "FAIL: $*" >&2
	failures=$((failures + 1))
}

value()
{
	if [ -r "$1" ]; then
		cat "$1"
	else
		echo "missing"
	fi
}

dt=/proc/device-tree/extcon-usb1
if [ ! -d "$dt" ]; then
	fail "missing /proc/device-tree/extcon-usb1"
else
	compatible=$(tr -d '\000' < "$dt/compatible")
	echo "dt.extcon_usb1.compatible=$compatible"
	if [ "$compatible" != "linux,extcon-usb-gpio" ]; then
		fail "extcon_usb1 compatible is not linux,extcon-usb-gpio"
	fi
	if [ -e "$dt/wakeup-source" ]; then
		fail "extcon_usb1 must not carry wakeup-source; the binding rejects it"
	fi
	if [ -r "$dt/vbus-gpios" ]; then
		printf 'dt.extcon_usb1.vbus-gpios='
		od -An -tx1 "$dt/vbus-gpios" | tr -s ' '
	else
		fail "extcon_usb1 lacks vbus-gpios"
	fi
fi

dev=/sys/bus/platform/devices/extcon-usb1
if [ ! -d "$dev" ]; then
	fail "missing platform device extcon-usb1"
else
	driver=$(basename "$(readlink -f "$dev/driver" 2>/dev/null)")
	echo "platform.extcon-usb1.driver=$driver"
	if [ "$driver" != "extcon-usb-gpio" ]; then
		fail "wrong extcon driver: $driver"
	fi

	wakeup=$(value "$dev/power/wakeup")
	echo "platform.extcon-usb1.wakeup=$wakeup"
	if [ "$wakeup" != "enabled" ]; then
		if [ "$require_enabled" -eq 1 ]; then
			fail "power/wakeup is not enabled"
		else
			echo "WARN: power/wakeup is not enabled"
		fi
	fi
fi

extcon=
for candidate in "$dev"/extcon/extcon*; do
	[ -e "$candidate" ] || continue
	extcon=$candidate
done
if [ -z "$extcon" ]; then
	for candidate in /sys/class/extcon/*; do
		[ -e "$candidate" ] || continue
		if [ "$(value "$candidate/name")" = "extcon-usb1" ]; then
			extcon=$candidate
			break
		fi
	done
fi
if [ -z "$extcon" ]; then
	fail "missing extcon class device for extcon-usb1"
else
	echo "extcon.class=$(basename "$extcon")"
	for state in "$extcon"/state/*; do
		[ -f "$state" ] || continue
		echo "extcon.$(basename "$state")=$(value "$state")"
	done
fi

irq_line=$(awk -F: '/extcon-usb1/ { print $1; exit }' /proc/interrupts)
if [ -z "$irq_line" ]; then
	fail "no extcon-usb1 IRQ in /proc/interrupts"
else
	irq=$(echo "$irq_line" | tr -d ' ')
	echo "irq.extcon-usb1=$irq"
	if [ -r "/sys/kernel/debug/irq/irqs/$irq/chip" ]; then
		echo "irq.extcon-usb1.chip=$(value "/sys/kernel/debug/irq/irqs/$irq/chip")"
	fi
	if [ -r "/sys/kernel/debug/irq/irqs/$irq/parent" ]; then
		echo "irq.extcon-usb1.parent=$(value "/sys/kernel/debug/irq/irqs/$irq/parent")"
	fi
fi

echo "power.wakeup_count=$(value /sys/power/wakeup_count)"
echo "power.pm_wakeup_irq=$(value /sys/power/pm_wakeup_irq)"
stats=/sys/kernel/debug/suspend_stats
for stat in success fail; do
	echo "suspend.$stat=$(awk -v key="$stat:" '$1 == key { print $2 }' "$stats" 2>/dev/null)"
done

if [ -r /sys/kernel/debug/wakeup_sources ]; then
	grep -E 'name|extcon-usb1' /sys/kernel/debug/wakeup_sources || true
fi

if dmesg 2>/dev/null | grep -Eiq \
	'(extcon-usb-gpio|extcon-usb1|spmi-pmic-arb|qcom-pdc).*(probe.*fail|failed|error|timeout)'; then
	echo "--- relevant dmesg tail ---"
	dmesg | grep -Ei \
		'(extcon-usb-gpio|extcon-usb1|spmi-pmic-arb|qcom-pdc)' | tail -n 80
	fail "extcon/SPMI/PDC error found in dmesg"
fi

if [ "$failures" -ne 0 ]; then
	echo "RESULT: USB VBUS wake baseline check failed ($failures finding(s))" >&2
	exit 1
fi

echo "RESULT: USB VBUS wake baseline check passed"
