#!/bin/sh
#
# Verify both physical Type-C plug orientations without suspending.
# Run over Wi-Fi SSH because flipping the plug disconnects NCM temporarily.
#
# Usage: test-usb-typec-orientation.sh [FLIPS] [WAIT_SECONDS] [OUTPUT]
#
set -u

FLIPS=${1:-2}
WAIT=${2:-90}
OUT=${3:-/var/log/samurai/typec-orientation-$(date +%s).log}

UDC_STATE=/sys/class/udc/a600000.usb/state
CARRIER=/sys/class/net/usb0/carrier
ONLINE=/sys/class/power_supply/mp2650-input/online
ORIENTATION=/sys/class/typec/port0/orientation
PARTNER=/sys/class/typec/port0-partner

read_value()
{
	cat "$1" 2>/dev/null | tr -d '[:space:]' || true
}

wait_opposite()
{
	want=$1
	i=0
	while [ "$i" -lt "$WAIT" ]; do
		now=$(read_value "$ORIENTATION")
		if [ "$now" != unknown ] && [ "$now" != "$want" ]; then
			return 0
		fi
		i=$((i + 1))
		sleep 1
	done
	return 1
}

wait_link()
{
	i=0
	while [ "$i" -lt 30 ]; do
		[ "$(read_value "$UDC_STATE")" = configured ] &&
			[ "$(read_value "$CARRIER")" = 1 ] && return 0
		i=$((i + 1))
		sleep 1
	done
	return 1
}

[ "$(id -u)" -eq 0 ] || {
	echo "ERROR: run as root" >&2
	exit 1
}
[ "$(read_value "$ONLINE")" = 1 ] || {
	echo "ERROR: VBUS must be online" >&2
	exit 1
}
[ -e "$PARTNER" ] || {
	echo "ERROR: no Type-C partner; attach the cable first" >&2
	exit 1
}
wait_link || {
	echo "ERROR: UDC/NCM is not configured before the test" >&2
	exit 1
}

mkdir -p "${OUT%/*}"
boot_id=$(cat /proc/sys/kernel/random/boot_id)
start_orientation=$(read_value "$ORIENTATION")
failures=0
seen_normal=0
seen_reverse=0
flip=1

printf 'schema=samurai-typec-orientation-v1\n' >"$OUT"
printf 'start=%s boot_id=%s flips=%s wait=%s initial=%s\n' \
	"$(date -Is)" "$boot_id" "$FLIPS" "$WAIT" "$start_orientation" >>"$OUT"

if [ "${DRY_RUN:-0}" = "1" ]; then
	printf 'DRY_RUN=1 orientation=%s partner=%s udc=%s carrier=%s online=%s\n' \
		"$start_orientation" "$([ -e "$PARTNER" ] && echo present || echo absent)" \
		"$(read_value "$UDC_STATE")" "$(read_value "$CARRIER")" \
		"$(read_value "$ONLINE")"
	exit 0
fi

while [ "$flip" -le "$FLIPS" ]; do
	before=$(read_value "$ORIENTATION")
	printf '\n*** FLIP THE TYPE-C PLUG NOW (waiting up to %s s, current=%s) ***\n' \
		"$WAIT" "$before"
	printf 'flip=%s action=wait_opposite before=%s\n' "$flip" "$before" >>"$OUT"

	if wait_opposite "$before"; then
		after=$(read_value "$ORIENTATION")
		printf 'flip=%s observed=%s\n' "$flip" "$after" >>"$OUT"
		if wait_link; then
			link=RECOVERED
		else
			link=LOST
			failures=$((failures + 1))
		fi
		printf 'flip=%s after=%s partner=%s udc=%s carrier=%s online=%s link=%s\n' \
			"$flip" "$after" "$([ -e "$PARTNER" ] && echo present || echo absent)" \
			"$(read_value "$UDC_STATE")" "$(read_value "$CARRIER")" \
			"$(read_value "$ONLINE")" "$link" | tee -a "$OUT"
		[ "$after" = normal ] && seen_normal=1
		[ "$after" = reverse ] && seen_reverse=1
	else
		printf 'flip=%s RESULT=TIMEOUT orientation=%s\n' \
			"$flip" "$(read_value "$ORIENTATION")" | tee -a "$OUT"
		failures=$((failures + 1))
	fi
	flip=$((flip + 1))
done

[ "$seen_normal" -eq 1 ] && [ "$seen_reverse" -eq 1 ] ||
	failures=$((failures + 1))
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$boot_id" ] ||
	failures=$((failures + 1))

{
	printf 'end=%s normal_seen=%s reverse_seen=%s failures=%s\n' \
		"$(date -Is)" "$seen_normal" "$seen_reverse" "$failures"
} >>"$OUT"

if [ "$failures" -eq 0 ]; then
	echo "RESULT: PASS" | tee -a "$OUT"
	exit 0
fi

echo "RESULT: FAIL" | tee -a "$OUT"
exit 1
