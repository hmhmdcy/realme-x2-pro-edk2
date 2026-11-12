#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
#
# Run a bounded RTC suspend on the OTG candidate.  Start this with nohup so
# the USB-NCM SSH connection may disappear without killing the test.
#
# Usage: test-usb-otg-suspend.sh [seconds] [--preflight-only]
#        [--staged] [--stages-only] [--require-dpm-watchdog]

set -u

root=${SAMURAI_SUSPEND_ROOT:-}
seconds=${1:-15}
case $seconds in
''|*[!0-9]*)
	echo "usage: $0 [seconds] [--preflight-only] [--staged] [--stages-only] [--require-dpm-watchdog]" >&2
	exit 2
	;;
esac
[ "$seconds" -ge 2 ] ||
	{
		echo "usage: $0 [seconds] [--preflight-only] [--staged] [--stages-only] [--require-dpm-watchdog]" >&2
		exit 2
	}
shift
preflight_only=0
staged=0
stages_only=0
require_dpm_watchdog=0
for argument in "$@"; do
	case $argument in
	--preflight-only) preflight_only=1 ;;
	--staged) staged=1 ;;
	--stages-only) staged=1; stages_only=1 ;;
	--require-dpm-watchdog) require_dpm_watchdog=1 ;;
	*)
		echo "usage: $0 [seconds] [--preflight-only] [--staged] [--stages-only] [--require-dpm-watchdog]" >&2
		exit 2
		;;
	esac
done

log=${SAMURAI_SUSPEND_LOG:-$root/var/log/samurai/usb-otg-suspend.log}
rtc=$root/sys/class/rtc/rtc0
pm_test=$root/sys/power/pm_test
dpm_watchdog=$root/sys/module/pm/parameters/dpm_watchdog_enabled
kernel_panic=$root/proc/sys/kernel/panic
pstore=$root/sys/fs/pstore
suspend_stats=$root/sys/power/suspend_stats

log_event()
{
	mkdir -p "${log%/*}"
	printf '%s %s\n' "$(date -Is)" "$*" >>"$log"
}

snapshot()
{
	state=$(cat "$root/sys/class/udc/a600000.usb/state" 2>/dev/null || echo missing)
	carrier=$(cat "$root/sys/class/net/usb0/carrier" 2>/dev/null || echo missing)
	success=$(cat "$root/sys/power/suspend_stats/success" 2>/dev/null || echo missing)
	fail=$(cat "$root/sys/power/suspend_stats/fail" 2>/dev/null || echo missing)
	pm_wakeup_irq=$(cat "$root/sys/power/pm_wakeup_irq" 2>/dev/null || echo missing)
	log_event "STATE udc=$state carrier=$carrier success=$success fail=$fail pm_wakeup_irq=$pm_wakeup_irq"
}

read_int()
{
	value=$(cat "$1" 2>/dev/null || true)
	case $value in
	''|*[!0-9]*) printf '0\n' ;;
	*) printf '%s\n' "$value" ;;
	esac
}

read_optional()
{
	cat "$1" 2>/dev/null || true
}

pm_test_saved=0
dpm_saved=0
saved_pm_test=
saved_dpm_watchdog=
saved_panic=

save_debug_controls()
{
	saved_pm_test=$(read_optional "$pm_test")
	pm_test_saved=1
	if [ "$require_dpm_watchdog" -eq 1 ]; then
		saved_dpm_watchdog=$(read_optional "$dpm_watchdog")
		saved_panic=$(read_optional "$kernel_panic")
		dpm_saved=1
	fi
}

restore_debug_controls()
{
	if [ "$pm_test_saved" -eq 1 ]; then
		printf '%s\n' "$saved_pm_test" >"$pm_test" 2>/dev/null || true
		pm_test_saved=0
	fi
	if [ "$dpm_saved" -eq 1 ]; then
		printf '%s\n' "$saved_dpm_watchdog" >"$dpm_watchdog" 2>/dev/null || true
		printf '%s\n' "$saved_panic" >"$kernel_panic" 2>/dev/null || true
		dpm_saved=0
	fi
}

enable_debug_watchdog()
{
	printf 'Y\n' >"$dpm_watchdog" || {
		log_event "FAIL cannot enable DPM watchdog"
		return 1
	}
	printf '30\n' >"$kernel_panic" || {
		log_event "FAIL cannot set kernel panic timeout"
		printf 'N\n' >"$dpm_watchdog" 2>/dev/null || true
		return 1
	}
	log_event "DPM_WATCHDOG enabled panic_timeout=30"
	return 0
}

rtc_irq_count()
{
	awk '
		/pm8xxx_rtc_alarm/ {
			for (i = 2; i <= NF; i++)
				if ($i ~ /^[0-9]+$/)
					sum += $i
		}
		END { print sum + 0 }
	' "$root/proc/interrupts" 2>/dev/null
}

rtc_preflight()
{
	preflight_failed=0
	mem_sleep=$(cat "$root/sys/power/mem_sleep" 2>/dev/null || echo missing)
	rtc_name=$(cat "$rtc/name" 2>/dev/null || echo missing)
	rtc_wakeup=$(cat "$rtc/device/power/wakeup" 2>/dev/null || echo missing)
	log_event "RTC_PREFLIGHT name=$rtc_name wakeup=$rtc_wakeup mem_sleep=$mem_sleep"
	usb_role=$(cat "$root"/sys/class/usb_role/*/role 2>/dev/null || echo missing)
	udc=$(cat "$root/sys/class/udc/a600000.usb/state" 2>/dev/null || echo missing)
	carrier=$(cat "$root/sys/class/net/usb0/carrier" 2>/dev/null || echo missing)
	vbus_online=$(cat "$root/sys/class/power_supply/mp2650-input/online" 2>/dev/null || echo missing)
	log_event "RTC_PREFLIGHT_LINK role=$usb_role udc=$udc carrier=$carrier vbus_online=$vbus_online"

	if [ ! -d "$rtc" ]; then
		log_event "FAIL rtc0 is missing"
		return 1
	fi
	[ "$rtc_wakeup" = enabled ] ||
		{ log_event "FAIL rtc0 wakeup=$rtc_wakeup"; preflight_failed=1; }
	[ -w "$rtc/wakealarm" ] ||
		{ log_event "FAIL rtc0 wakealarm is not writable"; preflight_failed=1; }
	case $mem_sleep in
	*'[s2idle]'*) ;;
	*)
		log_event "FAIL active mem_sleep is not s2idle"
		preflight_failed=1
		;;
	esac
	if ! grep -q pm8xxx_rtc_alarm "$root/proc/interrupts" 2>/dev/null; then
		log_event "FAIL pm8xxx_rtc_alarm IRQ is not registered"
		preflight_failed=1
	fi
	[ "$usb_role" = device ] ||
		{ log_event "FAIL DWC3 role=$usb_role, expected device"; preflight_failed=1; }
	[ "$udc" = configured ] ||
		{ log_event "FAIL UDC state=$udc, expected configured"; preflight_failed=1; }
	[ "$carrier" = 1 ] ||
		{ log_event "FAIL usb0 carrier=$carrier, expected 1"; preflight_failed=1; }
	[ "$vbus_online" = 1 ] ||
		{ log_event "FAIL VBUS online=$vbus_online, expected 1"; preflight_failed=1; }
	for host_bus in "$root"/sys/bus/usb/devices/usb*; do
		[ -e "$host_bus" ] || continue
		log_event "FAIL stale host root $(basename "$host_bus"); recover or reboot first"
		preflight_failed=1
	done
	if [ "$staged" -eq 1 ]; then
		[ -w "$pm_test" ] ||
			{ log_event "FAIL PM test control is missing or read-only"; preflight_failed=1; }
		[ -r "$suspend_stats/last_failed_dev" ] ||
			{ log_event "FAIL suspend_stats last_failed_dev is missing"; preflight_failed=1; }
	fi
	if [ "$require_dpm_watchdog" -eq 1 ]; then
		[ -w "$dpm_watchdog" ] ||
			{ log_event "FAIL DPM watchdog control is missing or read-only"; preflight_failed=1; }
		[ -w "$kernel_panic" ] ||
			{ log_event "FAIL kernel panic timeout is missing or read-only"; preflight_failed=1; }
		[ -d "$pstore" ] ||
			{ log_event "FAIL pstore is unavailable"; preflight_failed=1; }
	fi
	[ "$preflight_failed" -eq 0 ] || return 1

	printf '0\n' >"$rtc/wakealarm" || {
		log_event "FAIL cannot clear rtc0 wakealarm"
		return 1
	}
	irq_before=$(rtc_irq_count)
	printf '+3\n' >"$rtc/wakealarm" || {
		log_event "FAIL cannot arm rtc0 wakealarm"
		return 1
	}
	sleep 5
	irq_after=$(rtc_irq_count)
	wakealarm=$(cat "$rtc/wakealarm" 2>/dev/null || echo missing)
	log_event "RTC_ALARM_AWAKE irq_before=$irq_before irq_after=$irq_after wakealarm=$wakealarm"
	printf '0\n' >"$rtc/wakealarm" 2>/dev/null || true
	if [ "$irq_after" -le "$irq_before" ]; then
		log_event "FAIL awake RTC alarm did not raise pm8xxx_rtc_alarm"
		return 1
	fi
	return 0
}

run_pm_stage()
{
	stage=$1
	before_success=$(read_int "$suspend_stats/success")
	before_fail=$(read_int "$suspend_stats/fail")
	before_dev=$(read_optional "$suspend_stats/last_failed_dev")
	before_errno=$(read_optional "$suspend_stats/last_failed_errno")
	before_step=$(read_optional "$suspend_stats/last_failed_step")
	start_epoch=$(date +%s)
	printf '%s\n' "$stage" >"$pm_test" || {
		log_event "FAIL cannot select PM test stage=$stage"
		return 1
	}
	printf 'mem\n' >"$root/sys/power/state"
	rc=$?
	end_epoch=$(date +%s)
	elapsed=$((end_epoch - start_epoch))
	printf 'none\n' >"$pm_test" 2>/dev/null || true
	after_success=$(read_int "$suspend_stats/success")
	after_fail=$(read_int "$suspend_stats/fail")
	after_dev=$(read_optional "$suspend_stats/last_failed_dev")
	after_errno=$(read_optional "$suspend_stats/last_failed_errno")
	after_step=$(read_optional "$suspend_stats/last_failed_step")
	log_event "PM_TEST_STAGE stage=$stage rc=$rc elapsed_seconds=$elapsed success=$before_success->$after_success fail=$before_fail->$after_fail"
	log_event "PM_TEST_STAGE_DETAIL stage=$stage dev=$after_dev errno=$after_errno step=$after_step"
	[ "$rc" -eq 0 ] || {
		log_event "FAIL pm_test stage=$stage rc=$rc"
		return 1
	}
	[ "$after_success" -gt "$before_success" ] || {
		log_event "FAIL pm_test stage=$stage did not increment suspend success"
		return 1
	}
	[ "$after_fail" -eq "$before_fail" ] || {
		log_event "FAIL pm_test stage=$stage recorded a suspend failure"
		return 1
	}
	[ "$after_dev" = "$before_dev" ] &&
		[ "$after_errno" = "$before_errno" ] &&
		[ "$after_step" = "$before_step" ] || {
		log_event "FAIL pm_test stage=$stage changed last-failed device state"
		return 1
	}
	return 0
}

mkdir -p "${log%/*}"
log_event "BEGIN seconds=$seconds staged=$staged stages_only=$stages_only require_dpm_watchdog=$require_dpm_watchdog boot_id=$(cat "$root/proc/sys/kernel/random/boot_id" 2>/dev/null || echo unknown)"
snapshot
if ! rtc_preflight; then
	log_event "RESULT=FAIL preflight suspend_unproven"
	exit 1
fi
if [ "$preflight_only" -eq 1 ]; then
	log_event "RESULT=PASS preflight_only"
	exit 0
fi
if [ "${SAMURAI_SUSPEND_DETACHED:-0}" != 1 ]; then
	log_event "DETACH_START ssh=${SSH_CONNECTION:-none}"
	detached_args=$seconds
	[ "$staged" -eq 0 ] || detached_args="$detached_args --staged"
	[ "$stages_only" -eq 0 ] || detached_args="$detached_args --stages-only"
	[ "$require_dpm_watchdog" -eq 0 ] ||
		detached_args="$detached_args --require-dpm-watchdog"
	SAMURAI_SUSPEND_DETACHED=1 \
		nohup sh "$0" $detached_args >>"$log" 2>&1 &
	detached_pid=$!
	log_event "DETACHED pid=$detached_pid requested_seconds=$seconds staged=$staged stages_only=$stages_only require_dpm_watchdog=$require_dpm_watchdog"
	printf 'started detached suspend pid=%s; reconnect after the requested window\n' \
		"$detached_pid"
	exit 0
fi

save_debug_controls
trap restore_debug_controls EXIT
trap 'restore_debug_controls; exit 1' HUP INT TERM

rc=0
if [ "$require_dpm_watchdog" -eq 1 ]; then
	enable_debug_watchdog || rc=1
fi
if [ "$staged" -eq 1 ] && [ "$rc" -eq 0 ]; then
	for stage in freezer devices platform processors; do
		if ! run_pm_stage "$stage"; then
			log_event "RESULT=FAIL pm_test stage=$stage"
			rc=1
			break
		fi
	done
fi

if [ "$rc" -eq 0 ] && [ "$stages_only" -eq 0 ]; then
	start_epoch=$(date +%s)
	rtcwake -m mem -s "$seconds"
	rc=$?
	end_epoch=$(date +%s)
	elapsed=$((end_epoch - start_epoch))

	log_event "RTCWAKE_RC=$rc elapsed_seconds=$elapsed requested_seconds=$seconds"
	if [ "$elapsed" -lt $((seconds - 2)) ]; then
		log_event "FAIL early_wake elapsed_seconds=$elapsed requested_seconds=$seconds"
		rc=1
	fi
fi
snapshot
dmesg | grep -Ei 'PM: suspend|suspend exit|dwc3|typec|tcpm|xhci' |
	tail -n 80 >>"$log"
log_event "END boot_id=$(cat "$root/proc/sys/kernel/random/boot_id" 2>/dev/null || echo unknown)"

if [ "$rc" -eq 0 ]; then
	log_event "RESULT=PASS"
else
	log_event "RESULT=FAIL rc=$rc"
fi
[ "$rc" -eq 0 ]
