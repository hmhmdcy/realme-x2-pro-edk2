#!/bin/sh
# Verify that a PM8150B Type-C IRQ generated during s2idle wakes the SoC.
# This is not a physical cable test.
set -u

DURATION=${1:-30}
OUT=${2:-/root/typec-synthetic-wake-$(date +%s).log}
DEV=/sys/bus/platform/devices/c440000.spmi:pmic@2:typec@1500
PARAM=/sys/module/typec_irq_probe/parameters

: >"$OUT"
exec >>"$OUT" 2>&1

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
	echo "uptime=$(cut -d' ' -f1 /proc/uptime)"
	echo "rtc_epoch=$(cat /sys/class/rtc/rtc0/since_epoch)"
	echo "suspend_success=$(cat /sys/power/suspend_stats/success)"
	echo "suspend_fail=$(cat /sys/power/suspend_stats/fail)"
	echo "online=$(cat /sys/class/power_supply/mp2650-input/online)"
	echo "partner=$([ -e /sys/class/typec/port0-partner ] && echo 1 || echo 0)"
	echo "udc=$(cat /sys/class/udc/a600000.usb/state)"
	echo "carrier=$(cat /sys/class/net/usb0/carrier)"
	echo "cc_irq=$(irq_count cc-state-change)"
	echo "vbus_irq=$(irq_count vbus-change)"
	echo "attach_irq=$(irq_count attach-detach)"
	echo "sig_tx_irq=$(irq_count sig-tx)"
	grep -E '^c440000\.spmi:pmic@2:typec@1500|^tcpm-source-psy' \
		/sys/kernel/debug/wakeup_sources 2>/dev/null || true
}

if [ ! -d /sys/module/typec_irq_probe ]; then
	insmod /root/typec_irq_probe.ko || exit 1
fi

[ -e "$DEV/power/wakeup" ] || {
	echo "Type-C platform device is missing: $DEV"
	exit 1
}
case "$(cat "$DEV/power/wakeup" 2>/dev/null)" in
enabled) ;;
*) echo disabled >"$DEV/power/wakeup" ;;
esac
[ "$(cat "$DEV/power/wakeup")" = enabled ] || exit 1

snapshot before
echo "module_sha256=$(sha256sum /root/typec_irq_probe.ko | cut -d' ' -f1)"
echo 8000 >"$PARAM/delay_ms"
echo 1500 >"$PARAM/off_ms"
echo 1 >"$PARAM/armed"
echo "armed=$(cat "$PARAM/armed")"
sh /root/rtc-suspend.sh "$DURATION"
sleep 5
snapshot after
echo "=== DMESG ==="
dmesg | grep -E 'typec_irq_probe|PM: suspend|dwc3-qcom|qcom,pmic-typec' |
	tail -100

before_boot=$(awk -F= '/^boot_id=/{v=$2} END{print v}' "$OUT")
after_boot=$(awk -F= '/^boot_id=/{v=$2} END{print v}' "$OUT")
before_success=$(awk -F= '/^suspend_success=/{v=$2} END{print v}' "$OUT")
after_success=$(awk -F= '/^suspend_success=/{v=$2} END{print v}' "$OUT")
before_rtc=$(awk -F= '/^rtc_epoch=/{print $2; exit}' "$OUT")
after_rtc=$(awk -F= '/^rtc_epoch=/{v=$2} END{print v}' "$OUT")
cc_before=$(awk -F= '/^cc_irq=/{print $2; exit}' "$OUT")
cc_after=$(awk -F= '/^cc_irq=/{v=$2} END{print v}' "$OUT")
vbus_before=$(awk -F= '/^vbus_irq=/{print $2; exit}' "$OUT")
vbus_after=$(awk -F= '/^vbus_irq=/{v=$2} END{print v}' "$OUT")
attach_before=$(awk -F= '/^attach_irq=/{print $2; exit}' "$OUT")
attach_after=$(awk -F= '/^attach_irq=/{v=$2} END{print v}' "$OUT")
rtc_elapsed=$((after_rtc - before_rtc))
irq_delta=$((cc_after - cc_before + vbus_after - vbus_before + \
	attach_after - attach_before))

{
	echo "summary rtc_elapsed=$rtc_elapsed safety=$DURATION"
	echo "summary suspend=$before_success->$after_success boot_same=$([ "$before_boot" = "$after_boot" ] && echo yes || echo no)"
	echo "summary typec_irq_delta=$irq_delta"
} | tee -a "$OUT"

pass=1
[ "$before_boot" = "$after_boot" ] || pass=0
[ "$after_success" -gt "$before_success" ] || pass=0
[ "$rtc_elapsed" -lt "$((DURATION - 3))" ] || pass=0
[ "$irq_delta" -gt 0 ] || pass=0

if [ "$pass" -eq 1 ]; then
	echo "RESULT: PASS (synthetic Type-C IRQ wake; not a physical cable test)" |
		tee -a "$OUT"
	exit 0
fi
echo "RESULT: FAIL" | tee -a "$OUT"
exit 1
