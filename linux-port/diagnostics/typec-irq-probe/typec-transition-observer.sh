#!/bin/sh
#
# Diagnostic-only Type-C/VBUS transition observer.
#
# It records state changes while the phone is awake and also after a
# system resume.  It cannot prove which wake source fired, but it
# preserves the physical cable transition and the RTC/suspend counters
# for later correlation with the dedicated wake test.
#
set -u

OUT=${1:-/var/log/samurai/typec-transitions-$(date +%Y%m%d-%H%M%S).log}
mkdir -p "${OUT%/*}"

read_value()
{
	cat "$1" 2>/dev/null | tr -d '\r\n'
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

snapshot()
{
	printf 'online=%s partner=%s role=%s orient=%s udc=%s carrier=%s boot=%s success=%s fail=%s pmirq=%s tcpm=%s cc=%s vbus=%s attach=%s' \
		"$(read_value /sys/class/power_supply/mp2650-input/online)" \
		"$([ -e /sys/class/typec/port0-partner ] && echo 1 || echo 0)" \
		"$(read_value /sys/class/typec/port0/power_role)" \
		"$(read_value /sys/class/typec/port0/orientation)" \
		"$(read_value /sys/class/udc/a600000.usb/state)" \
		"$(read_value /sys/class/net/usb0/carrier)" \
		"$(read_value /proc/sys/kernel/random/boot_id)" \
		"$(read_value /sys/power/suspend_stats/success)" \
		"$(read_value /sys/power/suspend_stats/fail)" \
		"$(read_value /sys/power/suspend_stats/pm_wakeup_irq)" \
		"$(awk '$1 ~ /^tcpm-source-psy-/ { print $3; exit }' \
			/sys/kernel/debug/wakeup_sources 2>/dev/null)" \
		"$(irq_count cc-state-change)" \
		"$(irq_count vbus-change)" \
		"$(irq_count attach-detach)"
}

{
	echo "schema=samurai-typec-transition-observer-v1"
	echo "start=$(date -Is) log=$OUT"
} >>"$OUT"

previous=
while :; do
	current=$(snapshot)
	if [ "$current" != "$previous" ]; then
		printf '%s %s\n' "$(date -Is)" "$current" >>"$OUT"
		previous=$current
	fi
	sleep 1
done
