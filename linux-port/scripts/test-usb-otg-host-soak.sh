#!/bin/sh
# Read-only OTG host-mode soak.  It does not change roles, ports or VBUS.
set -eu

DURATION=${1:-600}
INTERVAL=${2:-10}
ROLE=/sys/class/typec/port0/data_role
URS=/sys/class/usb_role/a600000.usb-role-switch/role
START=$(awk '{ print int($1) }' /proc/uptime)

fail()
{
	echo "RESULT: FAIL $*" >&2
	exit 1
}

role_current()
{
	raw=$(cat "$ROLE" 2>/dev/null | tr -d '\n' || true)
	case $raw in
	*'['*']'*)
		printf '%s\n' "$raw" |
			sed -n 's/.*\[\([^]]*\)\].*/\1/p'
		;;
	*)
	printf '%s\n' "$raw" | tr -d '[:space:]'
		;;
	esac
}

xhci_present()
{
	for dev in /sys/bus/platform/drivers/xhci-hcd/xhci-hcd.*; do
		[ -d "$dev" ] && return 0
	done
	return 1
}

mode_request()
{
	dbus-send --system --type=method_call --print-reply \
		--reply-timeout=5000 \
		--dest=com.meego.usb_moded /com/meego/usb_moded \
		com.meego.usb_moded.mode_request 2>/dev/null |
		sed -n 's/.*string "\(.*\)"/\1/p' | tail -n 1
}

check()
{
	[ "$(role_current)" = host ] || fail "Type-C data_role is $(role_current)"
	[ "$(cat "$URS" 2>/dev/null)" = host ] || fail "URS role is not host"
	xhci_present || fail "xHCI device disappeared"
	[ "$(mode_request 2>/dev/null || true)" = host_mode ] ||
		fail "mode_request is not host_mode"
	[ ! -e /sys/class/net/usb0 ] || fail "stale usb0 appeared in host role"
}

check
samples=1
while :; do
	now=$(awk '{ print int($1) }' /proc/uptime)
	elapsed=$((now - START))
	[ "$elapsed" -lt "$DURATION" ] || break
	sleep "$INTERVAL"
	check
	samples=$((samples + 1))
	if [ $((samples % 6)) -eq 0 ]; then
		echo "soak t=${elapsed}s samples=$samples role=$(role_current) usb0=absent"
	fi
done

check
echo "RESULT: OTG host soak passed duration=${DURATION}s samples=$samples"
