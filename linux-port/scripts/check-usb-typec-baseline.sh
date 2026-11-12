#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
#
# Read-only USB2 Type-C gate for the RMX1931.  Run on the phone after booting
# a candidate DTB.  It never changes roles, VBUS or gadget state.

set -u

require_configured=0
if [ "${1:-}" = "--require-configured" ]; then
	require_configured=1
fi

failures=0

fail()
{
	echo "FAIL: $*" >&2
	failures=$((failures + 1))
}

value()
{
	path=$1
	if [ -r "$path" ]; then
		cat "$path"
	else
		echo "missing"
	fi
}

ports=$(find /sys/class/typec -maxdepth 1 -type l -name 'port*' 2>/dev/null | sort)
if [ -z "$ports" ]; then
	fail "no /sys/class/typec/port*; PM8150B TCPM did not register"
else
	for port in $ports; do
		echo "typec.$(basename "$port").power_role=$(value "$port/power_role")"
		echo "typec.$(basename "$port").data_role=$(value "$port/data_role")"
		echo "typec.$(basename "$port").port_type=$(value "$port/port_type")"
		echo "typec.$(basename "$port").orientation=$(value "$port/orientation")"
		echo "typec.$(basename "$port").vconn_role=$(value "$port/vconn_role")"
	done
fi

typec_dev=/sys/bus/platform/devices/c440000.spmi:pmic@2:typec@1500
typec_wake=$(value "$typec_dev/power/wakeup")
echo "typec.platform_wakeup=$typec_wake"
[ "$typec_wake" = enabled ] ||
	fail "$typec_dev/power/wakeup is not enabled"
if [ -r /sys/kernel/debug/wakeup_sources ]; then
	grep -q '^c440000\.spmi:pmic@2:typec@1500[[:space:]]' \
		/sys/kernel/debug/wakeup_sources ||
		fail "Type-C platform device is absent from wakeup_sources"
fi

udcs=$(find /sys/class/udc -maxdepth 1 -type l 2>/dev/null | sort)
if [ -z "$udcs" ]; then
	fail "no UDC registered"
else
	for udc in $udcs; do
		state=$(value "$udc/state")
		speed=$(value "$udc/current_speed")
		echo "udc.$(basename "$udc").state=$state"
		echo "udc.$(basename "$udc").current_speed=$speed"
		if [ "$require_configured" -eq 1 ] && [ "$state" != "configured" ]; then
			fail "UDC $(basename "$udc") is $state, expected configured"
		fi
	done
fi

carrier=$(value /sys/class/net/usb0/carrier)
echo "usb0.carrier=$carrier"
if [ "$require_configured" -eq 1 ] && [ "$carrier" != 1 ]; then
	fail "usb0 carrier is $carrier, expected 1"
fi

for role in /sys/class/usb_role/*; do
	[ -e "$role" ] || continue
	echo "usb_role.$(basename "$role").role=$(value "$role/role")"
done

if dmesg 2>/dev/null | grep -Eiq \
	'(pmic-typec|pm8150b.*typec|tcpm|dwc3).*(probe.*fail|failed|error|timeout)'; then
	echo "--- relevant dmesg tail ---"
	dmesg | grep -Ei \
		'(pmic-typec|pm8150b.*typec|tcpm|dwc3)' | tail -n 80
	fail "Type-C/DWC3 probe or runtime error found in dmesg"
fi

if [ "$failures" -ne 0 ]; then
	echo "RESULT: USB2 Type-C baseline check failed ($failures finding(s))" >&2
	exit 1
fi

echo "RESULT: USB2 Type-C baseline check passed"
