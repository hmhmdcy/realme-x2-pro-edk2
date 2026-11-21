#!/bin/sh
#
# Read-only gate for the PM8150B USBIN wake experiment.
#
# This checks that the samurai-usb-input observer is present in the runtime
# DT, that its PM8150B USBIN IRQs are registered, and that the power-supply
# wakeup source is enabled.  It does not suspend, plug, unplug or write to
# any USB, PMIC, charger or wakeup policy interface.

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

dt_value()
{
	if [ -r "$1" ]; then
		tr -d '\000' < "$1"
	else
		echo "missing"
	fi
}

sys_value()
{
	if [ -r "$1" ]; then
		cat "$1"
	else
		echo "missing"
	fi
}

irq_count()
{
	name=$1
	line=$(grep -E "[[:space:]]$name([[:space:]]|$)" /proc/interrupts 2>/dev/null | head -n 1)
	if [ -z "$line" ]; then
		echo 0
		return
	fi
	printf '%s\n' "$line" | awk '
		{
			sum = 0
			for (i = 2; i <= NF; i++)
				if ($i ~ /^[0-9]+$/)
					sum += $i
			print sum
		}
	'
}

wakeup_field()
{
	name=$1
	field=$2
	line=$(grep -E "^$name([[:space:]]|$)" /sys/kernel/debug/wakeup_sources 2>/dev/null | head -n 1)
	if [ -z "$line" ]; then
		echo 0
		return
	fi
	printf '%s\n' "$line" | awk -v f="$field" '{ print $f }'
}

dt=/proc/device-tree/soc@0
usb=$dt/usb@a600000
pmic=$dt/spmi@c440000/pmic@2
typec=$pmic/typec@1500
input=$pmic/w@1300

echo "runtime.dtb=$(sha256sum /sys/firmware/fdt 2>/dev/null | awk '{print $1}')"
echo "boot_id=$(cat /proc/sys/kernel/random/boot_id 2>/dev/null)"
echo "kernel=$(uname -r)"
echo "mem_sleep=$(cat /sys/power/mem_sleep 2>/dev/null)"

if [ -d "$input" ]; then
	echo "usb-input-node=present"
else
	fail "missing $input"
fi

compatible=$(dt_value "$input/compatible")
status=$(dt_value "$input/status")
interrupts=$(od -An -tx1 < "$input/interrupts" 2>/dev/null | tr -d ' \n')
echo "usb-input.compatible=$compatible"
echo "usb-input.status=$status"
echo "usb-input.interrupts-bytes=$interrupts"

[ "$compatible" = "realme,usb" ] ||
	fail "unexpected usb-input compatible"
[ "$status" = "okay" ] || [ "$status" = "missing" ] ||
	fail "usb-input status is not default/okay"
[ "$interrupts" = "00000002000000130000000400000003" ] ||
	fail "unexpected usb-input interrupt specifier"

typec_status=$(dt_value "$typec/status")
echo "typec.status=$typec_status"
[ "$typec_status" = "disabled" ] ||
	fail "PM8150B Type-C unexpectedly enabled"

dr_mode=$(dt_value "$usb/dr_mode")
echo "usb.dr_mode=$dr_mode"
[ "$dr_mode" = "peripheral" ] ||
	fail "DWC3 is not in peripheral mode"

if [ -e "$dt/extcon-usb1" ]; then
	fail "stale /extcon-usb1 node is present"
else
	echo "extcon-usb1=absent"
fi

if [ -e "$usb/snps,gadget-keep-connect-sys-sleep" ]; then
	fail "keep-connect opt-in is present"
else
	echo "keep-connect=absent"
fi

if [ -e "$usb/wakeup-source" ]; then
	fail "USB wakeup-source is present"
else
	echo "usb-wakeup-source=absent"
fi

psy=/sys/class/power_supply/samurai-usb-input
if [ -d "$psy" ]; then
	echo "power_supply=present"
	echo "online=$(sys_value "$psy/online")"
	echo "wakeup=$(sys_value "$psy/power/wakeup")"
else
	fail "missing $psy"
fi

usbin_irq=$(irq_count usbin-plugin)
echo "usbin-plugin.irq-count=$usbin_irq"
[ "$usbin_irq" -gt 0 ] || fail "usbin-plugin IRQ was not registered"

if [ -r /sys/kernel/debug/wakeup_sources ]; then
	echo "wakeup.events=$(wakeup_field samurai-usb-input 3)"
	echo "wakeup.count=$(wakeup_field samurai-usb-input 4)"
	grep -E "^samurai-usb-input([[:space:]]|$)" /sys/kernel/debug/wakeup_sources 2>/dev/null ||
		fail "samurai-usb-input is absent from wakeup_sources"
else
	echo "wakeup_sources=unavailable"
fi

udc=/sys/class/udc/a600000.usb
if [ -d "$udc" ]; then
	udc_state=$(sys_value "$udc/state")
	echo "udc.state=$udc_state"
	echo "udc.speed=$(sys_value "$udc/current_speed")"
	if [ "$require_configured" -eq 1 ] && [ "$udc_state" != "configured" ]; then
		fail "UDC is $udc_state, expected configured"
	fi
else
	fail "missing $udc"
fi

if [ -r /sys/power/suspend_stats/success ]; then
	echo "suspend.success=$(cat /sys/power/suspend_stats/success)"
	echo "suspend.fail=$(cat /sys/power/suspend_stats/fail)"
else
	echo "suspend_stats=unavailable"
fi

if [ "$failures" -ne 0 ]; then
	echo "RESULT: USB PMIC wake baseline failed ($failures finding(s))" >&2
	exit 1
fi

echo "RESULT: USB PMIC wake baseline passed"
