#!/bin/sh
# Offline check for staged pm_test execution and debug-control restoration.
set -eu

svc=${1:?usage: test-usb-otg-suspend-stages.sh SUSPEND_SCRIPT}
tmp=$(mktemp -d "${TMPDIR:-/tmp}/usb-otg-suspend-stages.XXXXXX")
state_reader=
rtc_helper=

cleanup()
{
	[ -z "$state_reader" ] || kill "$state_reader" 2>/dev/null || true
	[ -z "$rtc_helper" ] || kill "$rtc_helper" 2>/dev/null || true
	[ "${KEEP_TMP:-0}" = 1 ] || rm -rf "$tmp"
	[ "${KEEP_TMP:-0}" != 1 ] || printf 'kept temp tree %s\n' "$tmp" >&2
}
trap cleanup EXIT HUP INT TERM

root=$tmp/root
mkdir -p "$root/sys/class/rtc/rtc0/device/power"
mkdir -p "$root/sys/class/udc/a600000.usb"
mkdir -p "$root/sys/class/usb_role/a600000.usb-role-switch"
mkdir -p "$root/sys/class/net/usb0"
mkdir -p "$root/sys/class/power_supply/mp2650-input"
mkdir -p "$root/sys/power/suspend_stats"
mkdir -p "$root/sys/module/pm/parameters"
mkdir -p "$root/sys/fs/pstore"
mkdir -p "$root/proc/sys/kernel/random"
mkdir -p "$root/var/log/samurai"
mkdir -p "$tmp/bin"
mkfifo "$root/sys/power/state"

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
printf '\n' >"$root/sys/power/suspend_stats/last_failed_dev"
printf '0\n' >"$root/sys/power/suspend_stats/last_failed_errno"
printf '\n' >"$root/sys/power/suspend_stats/last_failed_step"
printf ' 42:      10       0       0       0       0       0  pm8xxx_rtc_alarm\n' \
	>"$root/proc/interrupts"
printf 'none\n' >"$root/sys/power/pm_test"
printf 'N\n' >"$root/sys/module/pm/parameters/dpm_watchdog_enabled"
printf '0\n' >"$root/proc/sys/kernel/panic"
printf '#!/bin/sh\nexit 0\n' >"$tmp/bin/dmesg"
chmod +x "$tmp/bin/dmesg"

(
	sleep 1
	printf ' 42:      11       0       0       0       0       0  pm8xxx_rtc_alarm\n' \
		>"$root/proc/interrupts"
) &
rtc_helper=$!

(
	while IFS= read -r state <"$root/sys/power/state"; do
		stage=$(cat "$root/sys/power/pm_test")
		success=$(cat "$root/sys/power/suspend_stats/success")
		printf '%s\n' "$((success + 1))" >"$root/sys/power/suspend_stats/success"
		printf '%s\n' "$stage" >"$root/sys/power/suspend_stats/last_test_stage"
	done
) &
state_reader=$!

PATH="$tmp/bin:$PATH" \
SAMURAI_SUSPEND_ROOT="$root" \
SAMURAI_SUSPEND_LOG="$root/var/log/samurai/usb-otg-suspend.log" \
SAMURAI_SUSPEND_DETACHED=1 \
	sh "$svc" 30 --stages-only --require-dpm-watchdog >/dev/null
wait "$rtc_helper"
rtc_helper=
kill "$state_reader" 2>/dev/null || true
wait "$state_reader" 2>/dev/null || true
state_reader=

log="$root/var/log/samurai/usb-otg-suspend.log"
cat "$log"
[ "$(wc -l <"$log")" -gt 0 ]
[ "$(grep -c 'PM_TEST_STAGE stage=' "$log")" -eq 4 ]
grep -q 'PM_TEST_STAGE stage=processors rc=0' "$log"
grep -q 'success=1->2' "$log"
grep -q 'success=2->3' "$log"
grep -q 'success=3->4' "$log"
grep -q 'success=4->5' "$log"
grep -q 'DPM_WATCHDOG enabled panic_timeout=30' "$log"
grep -q 'RESULT=PASS' "$log"
if grep -q 'RTCWAKE_RC=' "$log"; then
	echo "stages-only unexpectedly ran the full RTC suspend" >&2
	exit 1
fi
[ "$(cat "$root/sys/power/pm_test")" = none ]
[ "$(cat "$root/sys/module/pm/parameters/dpm_watchdog_enabled")" = N ]
[ "$(cat "$root/proc/sys/kernel/panic")" = 0 ]

echo "RESULT: suspend stages test passed"
