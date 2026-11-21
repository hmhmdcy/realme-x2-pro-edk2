#!/bin/sh
#
# Run repeated s2idle cycles and require the USB gadget link to recover.
# Usage: test-suspend-cycles.sh COUNT SECONDS OUTPUT_DIR
#
set -u

COUNT=${1:-3}
DURATION=${2:-15}
OUTDIR=${3:-/tmp/suspend-cycles-$(date +%s)}
BASE=$(dirname "$0")

mkdir -p "$OUTDIR"

wait_link()
{
	limit=$1
	i=0
	while [ "$i" -lt "$limit" ]; do
		state=$(cat /sys/class/udc/a600000.usb/state 2>/dev/null || true)
		carrier=$(cat /sys/class/net/usb0/carrier 2>/dev/null || true)
		if [ "$state" = "configured" ] && [ "$carrier" = "1" ]; then
			return 0
		fi
		i=$((i + 1))
		sleep 2
	done
	return 1
}

{
	echo "schema=samurai-suspend-cycles-v1"
	echo "count=$COUNT duration=$DURATION outdir=$OUTDIR"
	echo "start=$(date -Is) boot_id=$(cat /proc/sys/kernel/random/boot_id)"
} >"$OUTDIR/summary.txt"

cycle=1
failures=0
while [ "$cycle" -le "$COUNT" ]; do
	echo "=== cycle $cycle ==="
	if ! wait_link 30; then
		echo "cycle=$cycle RESULT=NO_LINK_BEFORE_SLEEP" | tee -a "$OUTDIR/summary.txt"
		failures=$((failures + 1))
		break
	fi

	"$BASE/test-suspend-baseline.sh" "$DURATION" "$OUTDIR/cycle-$cycle.log" \
		>"$OUTDIR/cycle-$cycle.stdout" 2>&1
	result=$(grep '^RESULT:' "$OUTDIR/cycle-$cycle.log" | tail -n 1 | cut -d' ' -f2-)
	before=$(grep '^suspend_success=' "$OUTDIR/cycle-$cycle.log" | head -n 1 | cut -d= -f2)
	after=$(grep '^suspend_success=' "$OUTDIR/cycle-$cycle.log" | tail -n 1 | cut -d= -f2)
	boot_before=$(grep '^boot_id=' "$OUTDIR/cycle-$cycle.log" | head -n 1 | cut -d= -f2)
	boot_after=$(grep '^boot_id=' "$OUTDIR/cycle-$cycle.log" | tail -n 1 | cut -d= -f2)
	elapsed=$(grep '^wall_elapsed=' "$OUTDIR/cycle-$cycle.log" | cut -d= -f2)

	sleep 18
	if wait_link 30; then
		link=RECOVERED
	else
		link=LOST
	fi

	echo "cycle=$cycle suspend=$result elapsed=$elapsed success=$before->$after boot_same=$([ "$boot_before" = "$boot_after" ] && echo yes || echo no) link=$link" \
		| tee -a "$OUTDIR/summary.txt"
	if [ "$result" != "SLEPT" ] || [ "$before" = "$after" ] ||
		[ "$boot_before" != "$boot_after" ] || [ "$link" != "RECOVERED" ]; then
		failures=$((failures + 1))
	fi
	cycle=$((cycle + 1))
done

echo "end=$(date -Is) failures=$failures" | tee -a "$OUTDIR/summary.txt"
if [ "$failures" -eq 0 ]; then
	echo "RESULT: PASS"
else
	echo "RESULT: FAIL"
fi
