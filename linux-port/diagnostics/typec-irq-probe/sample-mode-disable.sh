#!/bin/sh
# Sample VBUS/UDC state around a five-second TYPEC_DISABLE cycle.
set -eu

PARAM=/sys/module/typec_irq_probe/parameters
OUT=${1:-/root/typec-mode-disable-sample.log}

if [ ! -d /sys/module/typec_irq_probe ]; then
	insmod /root/typec_irq_probe.ko
fi

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

echo 5000 >"$PARAM/off_ms"
echo 1 >"$PARAM/run"

{
	echo "start=$(date -Is)"
	i=0
	while [ "$i" -lt 12 ]; do
		printf 't=%s online=%s udc=%s carrier=%s cc=%s vbus=%s attach=%s\n' \
			"$i" \
			"$(cat /sys/class/power_supply/mp2650-input/online 2>/dev/null)" \
			"$(cat /sys/class/udc/a600000.usb/state 2>/dev/null)" \
			"$(cat /sys/class/net/usb0/carrier 2>/dev/null)" \
			"$(irq_count cc-state-change)" \
			"$(irq_count vbus-change)" \
			"$(irq_count attach-detach)"
		i=$((i + 1))
		sleep 1
	done
	echo "end=$(date -Is)"
} >"$OUT" 2>&1

cat "$OUT"
