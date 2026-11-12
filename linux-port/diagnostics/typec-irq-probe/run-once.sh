#!/bin/sh
# Diagnostic helper for typec_irq_probe.ko.  Run as root on the target.
set -u

MODE=${1:-awake}
OUT=${2:-/root/typec-irq-probe-$MODE-$(date +%s).log}
PARAM=/sys/module/typec_irq_probe/parameters

case "$MODE" in
awake | suspend) ;;
*) echo "usage: $0 awake|suspend [LOG]" >&2; exit 2 ;;
esac

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
	echo "suspend_success=$(cat /sys/power/suspend_stats/success)"
	echo "suspend_fail=$(cat /sys/power/suspend_stats/fail)"
	echo "pm_wakeup_irq=$(cat /sys/power/suspend_stats/pm_wakeup_irq 2>/dev/null)"
	echo "online=$(cat /sys/class/power_supply/mp2650-input/online 2>/dev/null)"
	echo "partner=$([ -e /sys/class/typec/port0-partner ] && echo 1 || echo 0)"
	echo "power_role=$(cat /sys/class/typec/port0/power_role 2>/dev/null)"
	echo "data_role=$(cat /sys/class/typec/port0/data_role 2>/dev/null)"
	echo "orientation=$(cat /sys/class/typec/port0/orientation 2>/dev/null)"
	echo "udc=$(cat /sys/class/udc/a600000.usb/state 2>/dev/null)"
	echo "carrier=$(cat /sys/class/net/usb0/carrier 2>/dev/null)"
	echo "cc_irq=$(irq_count cc-state-change)"
	echo "vbus_irq=$(irq_count vbus-change)"
	echo "attach_irq=$(irq_count attach-detach)"
	echo "sig_tx_irq=$(irq_count sig-tx)"
	grep -E '^c440000\.spmi:pmic@2:typec@1500|^tcpm-source-psy' \
		/sys/kernel/debug/wakeup_sources 2>/dev/null || true
}

wait_link()
{
	i=0
	while [ "$i" -lt 60 ]; do
		if [ "$(cat /sys/class/udc/a600000.usb/state 2>/dev/null)" = configured ] &&
			[ "$(cat /sys/class/net/usb0/carrier 2>/dev/null)" = 1 ]; then
			return 0
		fi
		i=$((i + 1))
		sleep 1
	done
	return 1
}

{
	snapshot before
	echo "module_sha256=$(sha256sum /root/typec_irq_probe.ko | cut -d' ' -f1)"
	echo "mode=$MODE"
	if [ "$MODE" = suspend ]; then
		echo "armed=1"
		echo 1 >"$PARAM/armed"
		rtcwake -m mem -s 45
		echo "rtcwake_rc=$?"
	else
		echo 1 >"$PARAM/run"
		sleep 5
		if wait_link; then
			echo "link=RECOVERED"
		else
			echo "link=LOST"
		fi
	fi
	snapshot after
	echo "=== DMESG ==="
	dmesg | grep -E 'typec_irq_probe|PM: suspend|dwc3-qcom|qcom,pmic-typec' |
		tail -80
} >"$OUT" 2>&1

cat "$OUT"
