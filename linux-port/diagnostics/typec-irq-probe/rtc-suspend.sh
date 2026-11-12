#!/bin/sh
# Set a verified absolute pm8xxx RTC alarm, then request s2idle.
set -eu

delay=${1:-30}
alarm=/sys/class/rtc/rtc0/wakealarm
state=/sys/power/state

case "$delay" in
''|*[!0-9]*) echo "invalid delay: $delay" >&2; exit 2 ;;
esac

now=$(cat /sys/class/rtc/rtc0/since_epoch)
future=$((now + delay))
echo 0 >"$alarm"
echo "$future" >"$alarm"
armed=$(cat "$alarm")
if [ "$armed" != "$future" ]; then
	echo "alarm arm failed: wrote $future read $armed" >&2
	echo 0 >"$alarm" || true
	exit 1
fi

cleanup()
{
	echo 0 >"$alarm" 2>/dev/null || true
}
trap cleanup EXIT HUP INT TERM

printf 'rtc_now=%s rtc_alarm=%s delay=%s\n' "$now" "$future" "$delay"
printf 'RTC_ALARM_ARMED\n'
echo mem >"$state"
rc=$?
printf 'suspend_return=%s rtc_now=%s alarm_now=%s\n' "$rc" \
	"$(cat /sys/class/rtc/rtc0/since_epoch)" \
	"$(cat "$alarm")"
exit "$rc"
