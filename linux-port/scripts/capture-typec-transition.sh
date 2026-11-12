#!/bin/sh
#
# High-rate Type-C/VBUS transition sampler for host port power-cycle tests.
# Usage: capture-typec-transition.sh SECONDS [OUTPUT]
#
set -u

DURATION=${1:-20}
OUT=${2:-/tmp/typec-transition-$(date +%s).log}

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

online()
{
	cat /sys/class/power_supply/mp2650-input/online 2>/dev/null || echo 0
}

partner()
{
	[ -e /sys/class/typec/port0-partner ] && echo 1 || echo 0
}

read -r uptime _ </proc/uptime
end=$(awk -v now="$uptime" -v dur="$DURATION" 'BEGIN { printf "%.2f", now + dur }')

{
	echo "schema=samurai-typec-transition-v1"
	echo "start=$(date -Is) duration=$DURATION"
	echo "uptime_online_partner_cc_vbus_attach_udc_carrier_orientation"
	while :; do
		read -r now _ </proc/uptime
		if awk -v now="$now" -v end="$end" 'BEGIN { exit !(now >= end) }'; then
			break
		fi
		printf '%s %s %s %s %s %s %s %s %s %s\n' \
			"$now" \
			"$(online)" \
			"$(partner)" \
			"$(irq_count cc-state-change)" \
			"$(irq_count vbus-change)" \
			"$(irq_count attach-detach)" \
			"$(cat /sys/class/udc/a600000.usb/state 2>/dev/null || echo none)" \
			"$(cat /sys/class/net/usb0/carrier 2>/dev/null || echo 0)" \
			"$(cat /sys/class/typec/port0/orientation 2>/dev/null || echo none)"
		sleep 0.1
	done
	echo "end=$(date -Is)"
} >"$OUT" 2>&1

wc -l "$OUT"
