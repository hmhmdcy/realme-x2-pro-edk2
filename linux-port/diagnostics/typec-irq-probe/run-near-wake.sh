#!/bin/sh
# Test a PMIC Type-C disable issued at the system-suspend boundary.
set -u

DURATION=${1:-30}
OUT=${2:-/root/typec-near-wake-$(date +%s).log}
ARM=${ARM:-1}
DEV=/sys/bus/platform/devices/c440000.spmi:pmic@2:typec@1500
PARAM=/sys/module/typec_wake_near/parameters

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

snapshot()
{
	label=$1
	echo "=== $label ==="
	date -Is
	echo "boot_id=$(cat /proc/sys/kernel/random/boot_id)"
	echo "rtc_epoch=$(cat /sys/class/rtc/rtc0/since_epoch)"
	echo "suspend_success=$(cat /sys/power/suspend_stats/success)"
	echo "suspend_fail=$(cat /sys/power/suspend_stats/fail)"
	echo "online=$(cat /sys/class/power_supply/mp2650-input/online)"
	echo "udc=$(cat /sys/class/udc/a600000.usb/state)"
	echo "carrier=$(cat /sys/class/net/usb0/carrier)"
	echo "cc_irq=$(irq_count cc-state-change)"
	echo "vbus_irq=$(irq_count vbus-change)"
	echo "attach_irq=$(irq_count attach-detach)"
	tcpm_events=$(awk '$1 ~ /^tcpm-source-psy-/ { print $3; exit }' \
		/sys/kernel/debug/wakeup_sources 2>/dev/null)
	echo "tcpm_events=${tcpm_events:-0}"
	grep -E '^c440000\.spmi:pmic@2:typec@1500' \
		/sys/kernel/debug/wakeup_sources 2>/dev/null || true
}

if [ ! -d /sys/module/typec_wake_near ]; then
	insmod /root/typec_wake_near.ko || exit 1
fi
echo "$ARM" >"$PARAM/armed"

{
	snapshot before
	echo "armed=$(cat "$PARAM/armed")"
	sh /root/rtc-suspend.sh "$DURATION"
	sleep 4
	snapshot after
	echo "=== DMESG ==="
	dmesg | grep -E 'typec_wake_near|PM: suspend|qcom,pmic-typec|dwc3-qcom' |
		tail -120
} >"$OUT" 2>&1

echo 0 >"$PARAM/armed" 2>/dev/null || true

before_boot=$(awk -F= '/^boot_id=/{print $2; exit}' "$OUT")
after_boot=$(awk -F= '/^boot_id=/{v=$2} END{print v}' "$OUT")
before_success=$(awk -F= '/^suspend_success=/{print $2; exit}' "$OUT")
after_success=$(awk -F= '/^suspend_success=/{v=$2} END{print v}' "$OUT")
before_rtc=$(awk -F= '/^rtc_epoch=/{print $2; exit}' "$OUT")
after_rtc=$(awk -F= '/^rtc_epoch=/{v=$2} END{print v}' "$OUT")
before_cc=$(awk -F= '/^cc_irq=/{print $2; exit}' "$OUT")
after_cc=$(awk -F= '/^cc_irq=/{v=$2} END{print v}' "$OUT")
before_attach=$(awk -F= '/^attach_irq=/{print $2; exit}' "$OUT")
after_attach=$(awk -F= '/^attach_irq=/{v=$2} END{print v}' "$OUT")
before_tcpm=$(awk -F= '/^tcpm_events=/{print $2; exit}' "$OUT")
after_tcpm=$(awk -F= '/^tcpm_events=/{v=$2} END{print v}' "$OUT")
rtc_elapsed=$((after_rtc - before_rtc))
irq_delta=$((after_cc - before_cc + after_attach - before_attach))
tcpm_delta=$((after_tcpm - before_tcpm))

{
	echo "summary rtc_elapsed=$rtc_elapsed safety=$DURATION"
	echo "summary suspend=$before_success->$after_success boot_same=$([ "$before_boot" = "$after_boot" ] && echo yes || echo no)"
	echo "summary typec_irq_delta=$irq_delta"
	echo "summary tcpm_wake_events=$before_tcpm->$after_tcpm delta=$tcpm_delta"
} | tee -a "$OUT"

if [ "$ARM" = 0 ]; then
	control_pass=1
	[ "$before_boot" = "$after_boot" ] || control_pass=0
	[ "$after_success" -gt "$before_success" ] || control_pass=0
	[ "$rtc_elapsed" -ge "$((DURATION - 5))" ] || control_pass=0
	[ "$irq_delta" -eq 0 ] || control_pass=0
	if [ "$control_pass" -eq 1 ]; then
		echo "RESULT: CONTROL_PASS" | tee -a "$OUT"
		exit 0
	fi
	echo "RESULT: CONTROL_FAIL" | tee -a "$OUT"
	exit 1
fi

pass=1
[ "$before_boot" = "$after_boot" ] || pass=0
[ "$after_success" -gt "$before_success" ] || pass=0
[ "$rtc_elapsed" -lt "$((DURATION - 5))" ] || pass=0
[ "$irq_delta" -gt 0 ] || pass=0

if [ "$pass" -eq 1 ]; then
	echo "RESULT: PASS (boundary-generated Type-C event; not a cable test)" |
		tee -a "$OUT"
	exit 0
fi
echo "RESULT: FAIL" | tee -a "$OUT"
exit 1
