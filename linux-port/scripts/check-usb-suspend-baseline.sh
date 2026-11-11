#!/bin/sh
#
# Standard DWC3 gadget suspend/resume baseline.
#
# The board has no proven VBUS/attach source for the controller, so the
# unproven GPIO10 extcon and the keep-connect RFC opt-in must both be absent.
# The DWC3 PDC wake IRQs stay described in the SoC DT, but they are not armed
# by the peripheral suspend path.

set -u

fail=0
udc=/sys/class/udc/a600000.usb
usb_dt=/proc/device-tree/soc@0/usb@a600000

fatal()
{
	echo "FAIL: $*" >&2
	fail=1
}

[ -d "$udc" ] || fatal "missing $udc"
[ -d "$usb_dt" ] || fatal "missing $usb_dt"

if [ -e /proc/device-tree/extcon-usb1 ]; then
	fatal "unproven /extcon-usb1 node is present"
else
	echo "extcon-usb1=absent"
fi

if [ -e "$usb_dt/snps,gadget-keep-connect-sys-sleep" ]; then
	fatal "keep-connect opt-in is present"
else
	echo "keep-connect=absent"
fi

if [ -e "$usb_dt/wakeup-source" ]; then
	fatal "USB wakeup-source is present"
else
	echo "usb-wakeup-source=absent"
fi

echo "udc.state=$(cat "$udc/state" 2>/dev/null)"
echo "udc.speed=$(cat "$udc/current_speed" 2>/dev/null)"

if grep -q "dp_hs_phy_irq" /proc/interrupts; then
	echo "pdc-usb-irqs=present"
else
	fatal "PDC USB wake IRQs are missing"
fi

if grep -q "extcon-usb1" /proc/interrupts; then
	fatal "stale extcon-usb1 IRQ is present"
fi

if [ -r /sys/kernel/debug/suspend_stats ]; then
	head -2 /sys/kernel/debug/suspend_stats
else
	echo "suspend_stats=unavailable"
fi

if [ "$fail" -ne 0 ]; then
	echo "RESULT: USB suspend baseline check FAILED" >&2
	exit 1
fi

echo "RESULT: USB suspend baseline check passed"
