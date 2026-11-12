#!/bin/sh
#
# Exercise repeated gadget disconnect/connect cycles without touching VBUS.
# This validates host re-enumeration, NCM recovery and DWC3 recovery-service
# behavior while the cable remains physically attached.
#
# Usage: test-usb-soft-reconnect.sh [COUNT] [SECONDS_DISCONNECTED] [OUTDIR]
#
set -u

COUNT=${1:-20}
HOLD=${2:-2}
OUTDIR=${3:-/var/log/samurai/usb-soft-reconnect-$(date +%s)}
UDC=a600000.usb

UDC_STATE=/sys/class/udc/$UDC/state
SOFT_CONNECT=/sys/class/udc/$UDC/soft_connect
CARRIER=/sys/class/net/usb0/carrier
ONLINE=/sys/class/power_supply/mp2650-input/online
RECOVER_LOG=/var/log/samurai/usb-recover.log

mkdir -p "$OUTDIR"

read_value()
{
	cat "$1" 2>/dev/null | tr -d '[:space:]' || true
}

wait_state()
{
	want_configured=$1
	limit=$2
	i=0
	while [ "$i" -lt "$limit" ]; do
		state=$(read_value "$UDC_STATE")
		carrier=$(read_value "$CARRIER")
		if [ "$want_configured" -eq 1 ]; then
			[ "$state" = configured ] && [ "$carrier" = 1 ] && return 0
		else
			[ "$state" != configured ] && [ "$carrier" != 1 ] && return 0
		fi
		i=$((i + 1))
		sleep 1
	done
	return 1
}

[ "$(id -u)" -eq 0 ] || {
	echo "ERROR: run as root" >&2
	exit 1
}
[ -w "$SOFT_CONNECT" ] || {
	echo "ERROR: $SOFT_CONNECT is not writable" >&2
	exit 1
}
[ "$(read_value "$ONLINE")" = 1 ] || {
	echo "ERROR: VBUS must be online" >&2
	exit 1
}
wait_state 1 10 || {
	echo "ERROR: link is not configured before the test" >&2
	exit 1
}

boot_id=$(cat /proc/sys/kernel/random/boot_id)
recover_lines_before=$(wc -l <"$RECOVER_LOG" 2>/dev/null || echo 0)
failures=0
cycle=1

printf 'schema=samurai-usb-soft-reconnect-v1\n' >"$OUTDIR/summary.txt"
printf 'start=%s boot_id=%s count=%s hold=%s\n' \
	"$(date -Is)" "$boot_id" "$COUNT" "$HOLD" >>"$OUTDIR/summary.txt"

while [ "$cycle" -le "$COUNT" ]; do
	before_state=$(read_value "$UDC_STATE")
	before_carrier=$(read_value "$CARRIER")
	start=$(date +%s)

	if ! printf '%s\n' disconnect >"$SOFT_CONNECT"; then
		result=DISCONNECT_WRITE_FAILED
	elif ! wait_state 0 5; then
		result=DISCONNECT_TIMEOUT
	else
		sleep "$HOLD"
		if ! printf '%s\n' connect >"$SOFT_CONNECT"; then
			result=CONNECT_WRITE_FAILED
		elif ! wait_state 1 30; then
			result=RECONNECT_TIMEOUT
		else
			result=RECONNECTED
		fi
	fi

	elapsed=$(( $(date +%s) - start ))
	after_state=$(read_value "$UDC_STATE")
	after_carrier=$(read_value "$CARRIER")
	after_online=$(read_value "$ONLINE")
	printf 'cycle=%s result=%s elapsed=%s before=%s/%s after=%s/%s online=%s\n' \
		"$cycle" "$result" "$elapsed" "$before_state" "$before_carrier" \
		"$after_state" "$after_carrier" "$after_online" |
		tee -a "$OUTDIR/summary.txt"

	[ "$result" = RECONNECTED ] && [ "$after_online" = 1 ] ||
		failures=$((failures + 1))
	if [ "$(cat /proc/sys/kernel/random/boot_id)" != "$boot_id" ]; then
		echo "cycle=$cycle RESULT=BOOT_CHANGED" | tee -a "$OUTDIR/summary.txt"
		failures=$((failures + 1))
		break
	fi

	cycle=$((cycle + 1))
	sleep 2
done

recover_lines_after=$(wc -l <"$RECOVER_LOG" 2>/dev/null || echo 0)
recover_delta=$((recover_lines_after - recover_lines_before))
recover_events=$(tail -n "$recover_delta" "$RECOVER_LOG" 2>/dev/null |
	grep -E 'RECOVER_BEGIN|RECOVER_OK|RECOVER_FAIL|GIVE_UP' || true)

{
	printf 'end=%s failures=%s recover_log_delta=%s\n' \
		"$(date -Is)" "$failures" "$recover_delta"
	printf '%s\n' "$recover_events"
} >>"$OUTDIR/summary.txt"

if [ "$failures" -eq 0 ]; then
	echo "RESULT: PASS"
	exit 0
fi

echo "RESULT: FAIL"
exit 1
