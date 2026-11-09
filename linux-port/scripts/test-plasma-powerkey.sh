#!/bin/sh
# Observe a physical power-key test while the bridge owns the input device.
set -eu

duration=${1:-60}
case $duration in
''|*[!0-9]*) echo "usage: $0 [seconds]" >&2; exit 2 ;;
esac

if [ "$(id -u)" -ne 0 ]; then
	echo "run this as root" >&2
	exit 1
fi
if ! rc-service samurai-powerkey status >/dev/null 2>&1; then
	echo "samurai-powerkey service is not running" >&2
	exit 1
fi

log=/var/log/samurai-powerkey.log
bl=$(ls /sys/class/backlight/*/bl_power 2>/dev/null | head -n1 || true)
[ -n "$bl" ] || {
	echo "backlight bl_power device not found" >&2
	exit 1
}

before=$(wc -l <"$log" 2>/dev/null || echo 0)
echo "Press the physical power key once for a short-press test."
/usr/libexec/samurai-powerkey --status
echo "Current bl_power=$(cat "$bl")"

previous=$(cat "$bl")
end=$(( $(date +%s) + duration ))
while [ "$(date +%s)" -lt "$end" ]; do
	current=$(cat "$bl" 2>/dev/null || echo '?')
	if [ "$current" != "$previous" ]; then
		printf '%s bl_power=%s\n' "$(date '+%H:%M:%S')" "$current"
		previous=$current
	fi
	sleep 0.1
done

tail -n +$((before + 1)) "$log" 2>/dev/null || true
if tail -n +$((before + 1)) "$log" 2>/dev/null |
	grep -q 'physical power key press'; then
	echo "POWER_KEY_EVENT_SEEN"
else
	echo "NO_POWER_KEY_EVENT_SEEN"
fi
echo "Final bl_power=$(cat "$bl" 2>/dev/null || echo '?')"
/usr/libexec/samurai-powerkey --status
