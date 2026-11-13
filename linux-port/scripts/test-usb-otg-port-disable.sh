#!/bin/sh
# Hold the downstream xHCI port disabled to emulate a physical USB device
# unplug while the Type-C adapter stays connected.  The port is re-enabled
# in the cleanup trap even when the host role check fails.
set -eu

HOLD=${1:-40}
ROLE=/sys/class/typec/port0/data_role
PORT=

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

port_present()
{
	[ -r "$PORT/state" ] &&
		[ "$(cat "$PORT/state" 2>/dev/null | tr -d '[:space:]')" = configured ]
}

find_port()
{
	for candidate in /sys/bus/usb/devices/usb1/*/usb1-port*; do
		[ -w "$candidate/disable" ] || continue
		PORT=$candidate
		return 0
	done
	return 1
}

mode_request()
{
	command -v dbus-send >/dev/null 2>&1 || return 1
	dbus-send --system --type=method_call --print-reply \
		--reply-timeout=5000 \
		--dest=com.meego.usb_moded /com/meego/usb_moded \
		com.meego.usb_moded.mode_request 2>/dev/null |
		sed -n 's/.*string "\(.*\)"/\1/p' | tail -n 1
}

check_host()
{
	[ "$(role_current)" = host ] ||
		fail "Type-C data_role is $(role_current), expected host"
	xhci_present || fail "xHCI platform device disappeared"
	if command -v dbus-send >/dev/null 2>&1; then
		mode=$(mode_request 2>/dev/null || true)
		if [ -n "$mode" ] && [ "$mode" != host_mode ]; then
			fail "usb-moded mode_request=$mode, expected host_mode"
		fi
	fi
}

[ -r "$ROLE" ] || fail "missing $ROLE"
[ "$(role_current)" = host ] || fail "not in host mode"
[ -d /sys/bus/platform/drivers/xhci-hcd ] || fail "xHCI driver absent"
find_port || fail "no writable USB2 downstream port"

cleanup()
{
	printf '0\n' >"$PORT/disable" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "port=$PORT hold=${HOLD}s"
printf '1\n' >"$PORT/disable"
sleep 1
[ "$(cat "$PORT/state" 2>/dev/null | tr -d '[:space:]')" = "notattached" ] ||
	fail "port state is $(cat "$PORT/state" 2>/dev/null), expected notattached"

count=1
while [ "$count" -lt "$HOLD" ]; do
	sleep 1
	count=$((count + 1))
	check_host
	if [ $((count % 5)) -eq 0 ] || [ "$count" -eq 1 ]; then
		echo "t=$count role=$(role_current) port=$(cat "$PORT/state") mode=$(mode_request 2>/dev/null || true)"
	fi
done

printf '0\n' >"$PORT/disable"
sleep 5
check_host
port_present || fail "downstream port did not reattach"
echo "RESULT: port-disable host persistence passed hold=${HOLD}s"
