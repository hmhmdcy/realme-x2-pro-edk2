#!/bin/sh
#
# Test a physical Type-C cable event as a system wake source.
#
# Usage:
#   test-usb-typec-wake.sh insert [RTC_SAFETY_SECONDS]
#   test-usb-typec-wake.sh remove [RTC_SAFETY_SECONDS]
#
# insert: start with the cable unplugged (mp2650-input/online=0), run the
#         script, wait for the "SLEEPING" marker, then plug the cable.
# remove: start with the cable plugged and enumerated, run the script,
#         wait for the "SLEEPING" marker, then unplug the cable.
#
# The RTC alarm is only a safety timeout.  A PASS requires an early resume,
# a Type-C IRQ delta and the expected VBUS transition.
# A legacy A-to-C cable may expose no /sys/class/typec/port0-partner, so
# the test uses VBUS/UDC state as the cable-presence gate.
# The local printk clock is frozen across s2idle on this platform, so the RTC
# seconds are used to determine whether resume happened before the alarm.
#
set -u

MODE=${1:-}
DURATION=${2:-120}
OUT=${3:-/var/log/samurai/typec-wake-$MODE-$(date +%s).log}

die()
{
	printf 'ERROR: %s\n' "$*" >&2
	exit 1
}

case "$MODE" in
insert | remove) ;;
*) die "usage: $0 insert|remove [RTC_SAFETY_SECONDS] [OUTPUT]" ;;
esac

[ "$(id -u)" -eq 0 ] || die "run as root"
mkdir -p "${OUT%/*}"
[ -e /sys/class/typec/port0 ] || die "Type-C port0 is missing"
typec_wake=/sys/bus/platform/devices/c440000.spmi:pmic@2:typec@1500/power/wakeup
[ "$(cat "$typec_wake" 2>/dev/null)" = enabled ] ||
	die "Type-C platform wakeup is not enabled: $typec_wake"
printf '0\n' > /sys/class/rtc/rtc0/wakealarm 2>/dev/null || true

online()
{
	cat /sys/class/power_supply/mp2650-input/online 2>/dev/null || echo 0
}

udc_state()
{
	cat /sys/class/udc/a600000.usb/state 2>/dev/null || true
}

carrier()
{
	cat /sys/class/net/usb0/carrier 2>/dev/null || echo 0
}

irq_count()
{
	awk -v name="$1" '
		$0 ~ name {
			sum = 0
			for (i = 2; i <= NF - 3; i++)
				if ($i ~ /^[0-9]+$/)
					sum += $i
			print sum
			exit
		}
	' /proc/interrupts
}

irq_snapshot()
{
	printf 'cc_state_change=%s\n' "$(irq_count cc-state-change)"
	printf 'vbus_change=%s\n' "$(irq_count vbus-change)"
	printf 'attach_detach=%s\n' "$(irq_count attach-detach)"
	printf 'sig_tx=%s\n' "$(irq_count sig-tx)"
}

typec_snapshot()
{
	printf 'online=%s\n' "$(online)"
	printf 'partner=%s\n' "$([ -e /sys/class/typec/port0-partner ] && echo 1 || echo 0)"
	printf 'power_role=%s\n' "$(cat /sys/class/typec/port0/power_role 2>/dev/null)"
	printf 'data_role=%s\n' "$(cat /sys/class/typec/port0/data_role 2>/dev/null)"
	printf 'orientation=%s\n' "$(cat /sys/class/typec/port0/orientation 2>/dev/null)"
	printf 'udc=%s\n' "$(udc_state)"
	printf 'carrier=%s\n' "$(carrier)"
	printf 'tcpm_events=%s\n' "$(awk '
		$1 ~ /^tcpm-source-psy-/ { print $3; exit }
	' /sys/kernel/debug/wakeup_sources 2>/dev/null)"
}

wait_link()
{
	i=0
	while [ "$i" -lt 30 ]; do
		if [ "$(udc_state)" = "configured" ] && [ "$(carrier)" = "1" ]; then
			return 0
		fi
		i=$((i + 1))
		sleep 2
	done
	return 1
}

wait_online()
{
	expected=$1
	i=0
	while [ "$i" -lt 30 ]; do
		[ "$(online)" = "$expected" ] && return 0
		i=$((i + 1))
		sleep 1
	done
	return 1
}

if [ "$MODE" = insert ]; then
	[ "$(online)" = "0" ] ||
		die "insert test must start with VBUS offline; unplug the cable first"
	[ "$(udc_state)" != "configured" ] ||
		die "insert test still has UDC configured; wait for detach and retry"
	ACTION="plug the cable in"
else
	[ "$(online)" = "1" ] ||
		die "remove test must start with VBUS online; plug and enumerate first"
	[ "$(udc_state)" = "configured" ] ||
		die "remove test must start with UDC configured: $(udc_state)"
	ACTION="unplug the cable"
fi

if [ "${DRY_RUN:-0}" = "1" ]; then
	echo "DRY_RUN=1 mode=$MODE duration=$DURATION"
	typec_snapshot
	irq_snapshot
	exit 0
fi

printf 'Type-C wake test: %s. Suspend starts in 8 seconds; then %s.\n' \
	"$MODE" "$ACTION"
printf 'RTC safety timeout: %s seconds. Log: %s\n' "$DURATION" "$OUT"

{
	echo "=== BEFORE ==="
	date -Is
	echo "mode=$MODE duration=$DURATION"
	echo "boot_id=$(cat /proc/sys/kernel/random/boot_id)"
	echo "suspend_success=$(cat /sys/power/suspend_stats/success)"
	echo "suspend_fail=$(cat /sys/power/suspend_stats/fail)"
	echo "epoch=$(date +%s)"
	echo "rtc_epoch=$(cat /sys/class/rtc/rtc0/since_epoch 2>/dev/null)"
	echo "rtc_wakealarm=$(cat /sys/class/rtc/rtc0/wakealarm 2>/dev/null)"
	typec_snapshot
	irq_snapshot
	echo "--- wakeup_sources ---"
	cat /sys/kernel/debug/wakeup_sources 2>/dev/null |
		grep -Ei 'typec|pmic|rtc' || true
	echo "=== ACTION ==="
	echo "After this line the phone will suspend in 8 seconds."
	echo "Then ${ACTION} and do not touch anything else."
	echo "RTC safety wake: ${DURATION} seconds."
} >"$OUT" 2>&1

printf '\n*** SUSPEND IN 8 SECONDS: %s ***\n' "$ACTION"
i=8
while [ "$i" -gt 0 ]; do
	printf '%s ' "$i"
	sleep 1
	i=$((i - 1))
done
printf '\n*** SLEEPING NOW: %s ***\n' "$ACTION"
echo "SLEEPING" >>"$OUT"

{
	start=$(date +%s)
	rtc_before=$(cat /sys/class/rtc/rtc0/since_epoch 2>/dev/null)
	rtcwake -m mem -s "$DURATION"
	rc=$?
	end=$(date +%s)
	rtc_after=$(cat /sys/class/rtc/rtc0/since_epoch 2>/dev/null)
	echo "rtcwake_rc=$rc"
	echo "wall_elapsed=$((end - start))"
	echo "rtc_elapsed=$((rtc_after - rtc_before))"
	if [ "$MODE" = insert ]; then
		wait_online 1 || true
	else
		wait_online 0 || true
	fi
	echo "=== AFTER ==="
	date -Is
	echo "boot_id=$(cat /proc/sys/kernel/random/boot_id)"
	echo "suspend_success=$(cat /sys/power/suspend_stats/success)"
	echo "suspend_fail=$(cat /sys/power/suspend_stats/fail)"
	echo "last_failed_dev=$(cat /sys/power/suspend_stats/last_failed_dev 2>/dev/null)"
	echo "last_failed_errno=$(cat /sys/power/suspend_stats/last_failed_errno 2>/dev/null)"
	echo "pm_wakeup_irq=$(cat /sys/power/suspend_stats/pm_wakeup_irq 2>/dev/null)"
	echo "epoch=$(date +%s)"
	echo "rtc_epoch=$(cat /sys/class/rtc/rtc0/since_epoch 2>/dev/null)"
	typec_snapshot
	irq_snapshot
	echo "--- wakeup_sources ---"
	cat /sys/kernel/debug/wakeup_sources 2>/dev/null |
		grep -Ei 'typec|pmic|rtc' || true
	echo "--- recovery wait ---"
	if [ "$MODE" = insert ]; then
		if wait_link; then
			echo "link=RECOVERED udc=$(udc_state) carrier=$(carrier)"
		else
			echo "link=LOST udc=$(udc_state) carrier=$(carrier)"
		fi
	fi
	echo "=== RESULT ==="
} >>"$OUT" 2>&1

before_boot=$(grep '^boot_id=' "$OUT" | head -n 1 | cut -d= -f2)
after_boot=$(grep '^boot_id=' "$OUT" | tail -n 1 | cut -d= -f2)
before_success=$(grep '^suspend_success=' "$OUT" | head -n 1 | cut -d= -f2)
after_success=$(grep '^suspend_success=' "$OUT" | tail -n 1 | cut -d= -f2)
before_online=$(grep '^online=' "$OUT" | head -n 1 | cut -d= -f2)
after_online=$(grep '^online=' "$OUT" | tail -n 1 | cut -d= -f2)
before_cc=$(grep '^cc_state_change=' "$OUT" | head -n 1 | cut -d= -f2)
after_cc=$(grep '^cc_state_change=' "$OUT" | tail -n 1 | cut -d= -f2)
before_vbus=$(grep '^vbus_change=' "$OUT" | head -n 1 | cut -d= -f2)
after_vbus=$(grep '^vbus_change=' "$OUT" | tail -n 1 | cut -d= -f2)
before_attach=$(grep '^attach_detach=' "$OUT" | head -n 1 | cut -d= -f2)
after_attach=$(grep '^attach_detach=' "$OUT" | tail -n 1 | cut -d= -f2)
before_tcpm=$(grep '^tcpm_events=' "$OUT" | head -n 1 | cut -d= -f2)
after_tcpm=$(grep '^tcpm_events=' "$OUT" | tail -n 1 | cut -d= -f2)
before_tcpm=${before_tcpm:-0}
after_tcpm=${after_tcpm:-0}
elapsed=$(grep '^wall_elapsed=' "$OUT" | cut -d= -f2)
rtc_elapsed=$(grep '^rtc_elapsed=' "$OUT" | cut -d= -f2)
rtc_elapsed=${rtc_elapsed:-0}
pm_irq=$(grep '^pm_wakeup_irq=' "$OUT" | cut -d= -f2-)
rtc_irq=$(awk '$0 ~ /pm8xxx_rtc_alarm/ {
	gsub(":", "", $1)
	print $1
	exit
}' /proc/interrupts)

cc_delta=$((after_cc - before_cc))
vbus_delta=$((after_vbus - before_vbus))
attach_delta=$((after_attach - before_attach))
irq_delta=$((cc_delta + vbus_delta + attach_delta))
tcpm_delta=$((after_tcpm - before_tcpm))

{
	echo "summary mode=$MODE wall_elapsed=$elapsed rtc_elapsed=$rtc_elapsed success=$before_success->$after_success"
	echo "summary boot_same=$([ "$before_boot" = "$after_boot" ] && echo yes || echo no)"
	echo "summary online=$before_online->$after_online"
	echo "summary irq_delta cc=$cc_delta vbus=$vbus_delta attach=$attach_delta total=$irq_delta"
	echo "summary tcpm_events=$before_tcpm->$after_tcpm delta=$tcpm_delta"
	echo "summary pm_wakeup_irq=$pm_irq"
	echo "summary rtc_alarm_irq=${rtc_irq:-unknown}"
} | tee -a "$OUT"

pass=1
[ "$rc" -eq 0 ] || pass=0
[ "$rtc_elapsed" -lt "$((DURATION - 5))" ] || pass=0
[ "$before_boot" = "$after_boot" ] || pass=0
[ "$after_success" -gt "$before_success" ] || pass=0
[ "$irq_delta" -gt 0 ] || pass=0
if [ -n "$rtc_irq" ] && [ "$pm_irq" = "$rtc_irq" ]; then
	pass=0
fi
if [ "$MODE" = insert ]; then
	[ "$before_online" = "0" ] && [ "$after_online" = "1" ] || pass=0
else
	[ "$before_online" = "1" ] && [ "$after_online" = "0" ] || pass=0
fi

if [ "$pass" -eq 1 ]; then
	echo "RESULT: PASS" | tee -a "$OUT"
	exit 0
fi

echo "RESULT: FAIL" | tee -a "$OUT"
exit 1
