#!/bin/sh
#
# Bounded s2idle smoke test using the RTC interface that previously passed.
# Run on the handset only with a physical recovery path available.
#
set -u

seconds=${1:-30}
log=${2:-/tmp/samurai-suspend-rtcwake.log}

if [ "${SAMURAI_ALLOW_SUSPEND:-0}" != "1" ]; then
	echo "refusing suspend: set SAMURAI_ALLOW_SUSPEND=1 and keep a physical recovery path" >&2
	exit 2
fi

case "$seconds" in
*[!0-9]*|'')
	echo "usage: $0 [seconds] [log]" >&2
	exit 2
	;;
esac

exec >>"$log" 2>&1

echo "BEGIN=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "BOOT_BEFORE=$(cat /proc/sys/kernel/random/boot_id)"
echo "UPTIME_BEFORE=$(cat /proc/uptime)"
echo "STATE=$(cat /sys/power/state)"
echo "MEM_SLEEP=$(cat /sys/power/mem_sleep)"
echo "WAKEALARM_BEFORE=$(cat /sys/class/rtc/rtc0/wakealarm)"
sync

rtcwake -m mem -s "$seconds"
rc=$?

echo "RTCWAKE_RC=$rc"
echo "BOOT_AFTER=$(cat /proc/sys/kernel/random/boot_id)"
echo "UPTIME_AFTER=$(cat /proc/uptime)"
echo "WAKEALARM_AFTER=$(cat /sys/class/rtc/rtc0/wakealarm)"
for file in /sys/kernel/debug/suspend_stats/*; do
	[ -f "$file" ] || continue
	printf '%s=' "$(basename "$file")"
	cat "$file"
done
echo "DONE=$(date -u +%Y-%m-%dT%H:%M:%SZ)"

exit "$rc"
