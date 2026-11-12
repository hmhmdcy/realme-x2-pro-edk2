#!/bin/sh
# Offline test for the non-suspending RTC safety gate used by the OTG
# suspend diagnostic.
set -eu

svc=${1:?usage: test-usb-otg-suspend-preflight.sh SUSPEND_SCRIPT}
tmp=$(mktemp -d "${TMPDIR:-/tmp}/usb-otg-suspend-preflight.XXXXXX")
helper=

cleanup()
{
	[ -z "$helper" ] || kill "$helper" 2>/dev/null || true
	rm -rf "$tmp"
}
trap cleanup EXIT HUP INT TERM

prepare_tree()
{
	root=$1
	mkdir -p "$root/sys/class/rtc/rtc0/device/power"
	mkdir -p "$root/sys/class/udc/a600000.usb"
	mkdir -p "$root/sys/class/usb_role/a600000.usb-role-switch"
	mkdir -p "$root/sys/class/net/usb0"
	mkdir -p "$root/sys/class/power_supply/mp2650-input"
	mkdir -p "$root/sys/power/suspend_stats"
	mkdir -p "$root/proc/sys/kernel/random"
	mkdir -p "$root/var/log/samurai"
	printf 'pm8xxx_rtc_alarm' >"$root/proc/sys/kernel/random/boot_id"
	printf '[s2idle] deep\n' >"$root/sys/power/mem_sleep"
	printf 'enabled\n' >"$root/sys/class/rtc/rtc0/device/power/wakeup"
	printf 'rtc-pm8xxx\n' >"$root/sys/class/rtc/rtc0/name"
	: >"$root/sys/class/rtc/rtc0/wakealarm"
	printf 'configured\n' >"$root/sys/class/udc/a600000.usb/state"
	printf 'device\n' >"$root/sys/class/usb_role/a600000.usb-role-switch/role"
	printf '1\n' >"$root/sys/class/net/usb0/carrier"
	printf '1\n' >"$root/sys/class/power_supply/mp2650-input/online"
	printf '1\n' >"$root/sys/power/suspend_stats/success"
	printf '0\n' >"$root/sys/power/suspend_stats/fail"
	printf '0\n' >"$root/sys/power/pm_wakeup_irq"
	printf ' 42:      10       0       0       0       0       0  pm8xxx_rtc_alarm\n' \
		>"$root/proc/interrupts"
}

prepare_debug_controls()
{
	root=$1
	mkdir -p "$root/sys/module/pm/parameters"
	mkdir -p "$root/sys/fs/pstore"
	mkdir -p "$root/proc/sys/kernel"
	printf 'none\n' >"$root/sys/power/pm_test"
	printf 'N\n' >"$root/sys/module/pm/parameters/dpm_watchdog_enabled"
	printf '0\n' >"$root/proc/sys/kernel/panic"
	printf '\n' >"$root/sys/power/suspend_stats/last_failed_dev"
	printf '0\n' >"$root/sys/power/suspend_stats/last_failed_errno"
	printf '\n' >"$root/sys/power/suspend_stats/last_failed_step"
}

positive=$tmp/positive
prepare_tree "$positive"
(
	sleep 1
	printf ' 42:      11       0       0       0       0       0  pm8xxx_rtc_alarm\n' \
		>"$positive/proc/interrupts"
) &
helper=$!

SAMURAI_SUSPEND_ROOT="$positive" \
SAMURAI_SUSPEND_LOG="$positive/var/log/samurai/usb-otg-suspend.log" \
	sh "$svc" 30 --preflight-only >/dev/null
wait "$helper"
helper=
cat "$positive/var/log/samurai/usb-otg-suspend.log"
grep -q 'RTC_PREFLIGHT name=rtc-pm8xxx wakeup=enabled' \
	"$positive/var/log/samurai/usb-otg-suspend.log"
grep -q 'RTC_PREFLIGHT_LINK role=device udc=configured carrier=1 vbus_online=1' \
	"$positive/var/log/samurai/usb-otg-suspend.log"
grep -q 'RTC_ALARM_AWAKE irq_before=10 irq_after=11' \
	"$positive/var/log/samurai/usb-otg-suspend.log"
grep -q 'RESULT=PASS preflight_only' \
	"$positive/var/log/samurai/usb-otg-suspend.log"
if grep -q 'DETACHED' \
	"$positive/var/log/samurai/usb-otg-suspend.log"; then
	echo "preflight-only unexpectedly detached a suspend worker" >&2
	exit 1
fi

negative=$tmp/negative
prepare_tree "$negative"
printf 'disabled\n' >"$negative/sys/class/rtc/rtc0/device/power/wakeup"
if SAMURAI_SUSPEND_ROOT="$negative" \
	SAMURAI_SUSPEND_LOG="$negative/var/log/samurai/usb-otg-suspend.log" \
	sh "$svc" 30 --preflight-only >/dev/null 2>&1; then
	echo "negative case unexpectedly passed" >&2
	exit 1
fi
cat "$negative/var/log/samurai/usb-otg-suspend.log"
grep -q 'FAIL rtc0 wakeup=disabled' \
	"$negative/var/log/samurai/usb-otg-suspend.log"
grep -q 'RESULT=FAIL preflight suspend_unproven' \
	"$negative/var/log/samurai/usb-otg-suspend.log"
if grep -q 'RTC_ALARM_AWAKE' \
	"$negative/var/log/samurai/usb-otg-suspend.log"; then
	echo "negative case armed an alarm before passing preflight" >&2
	exit 1
fi

debug_negative=$tmp/debug-negative
prepare_tree "$debug_negative"
if SAMURAI_SUSPEND_ROOT="$debug_negative" \
	SAMURAI_SUSPEND_LOG="$debug_negative/var/log/samurai/usb-otg-suspend.log" \
	sh "$svc" 30 --preflight-only --staged >/dev/null 2>&1; then
	echo "missing PM debug controls unexpectedly passed --staged" >&2
	exit 1
fi
grep -q 'FAIL PM test control is missing or read-only' \
	"$debug_negative/var/log/samurai/usb-otg-suspend.log"

debug_positive=$tmp/debug-positive
prepare_tree "$debug_positive"
prepare_debug_controls "$debug_positive"
(
	sleep 1
	printf ' 42:      11       0       0       0       0       0  pm8xxx_rtc_alarm\n' \
		>"$debug_positive/proc/interrupts"
) &
helper=$!
SAMURAI_SUSPEND_ROOT="$debug_positive" \
SAMURAI_SUSPEND_LOG="$debug_positive/var/log/samurai/usb-otg-suspend.log" \
	sh "$svc" 30 --preflight-only --staged --require-dpm-watchdog >/dev/null
wait "$helper"
helper=
grep -q 'RESULT=PASS preflight_only' \
	"$debug_positive/var/log/samurai/usb-otg-suspend.log"

echo "RESULT: suspend preflight test passed"
