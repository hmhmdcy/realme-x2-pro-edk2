#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
#
# Run a bounded RTC suspend on the OTG candidate.  Start this with nohup so
# the USB-NCM SSH connection may disappear without killing the test.
#
# Usage: test-usb-otg-suspend.sh [seconds] [--preflight-only]

set -u

root=${SAMURAI_SUSPEND_ROOT:-}
seconds=${1:-15}
case $seconds in
''|*[!0-9]*) echo "usage: $0 [seconds] [--preflight-only]" >&2; exit 2 ;;
esac
[ "$seconds" -ge 2 ] ||
	{ echo "usage: $0 [seconds] [--preflight-only]" >&2; exit 2; }
preflight_only=0
if [ "${2:-}" = --preflight-only ]; then
	preflight_only=1
elif [ -n "${2:-}" ]; then
	echo "usage: $0 [seconds] [--preflight-only]" >&2
	exit 2
fi

log=${SAMURAI_SUSPEND_LOG:-$root/var/log/samurai/usb-otg-suspend.log}
rtc=$root/sys/class/rtc/rtc0

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

mkdir -p "${log%/*}"
log_event "BEGIN seconds=$seconds boot_id=$(cat "$root/proc/sys/kernel/random/boot_id" 2>/dev/null || echo unknown)"
snapshot
if ! rtc_preflight; then
	log_event "RESULT=FAIL preflight rtc0_alarm_unproven"
	exit 1
fi
if [ "$preflight_only" -eq 1 ]; then
	log_event "RESULT=PASS preflight_only"
	exit 0
fi

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
