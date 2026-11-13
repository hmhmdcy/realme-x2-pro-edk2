#!/bin/sh
# Restart usb-signaller repeatedly and verify its default Developer mode
# reaches the UDC without activating NCM at carrier 0.  Each round restores
# the standard Type-C/DWC3 host role before the next restart.
set -eu

CYCLES=${1:-3}
ROLE=/sys/class/typec/port0/data_role
URS=/sys/class/usb_role/a600000.usb-role-switch/role
UDC=/sys/class/udc/a600000.usb

fail()
{
	echo "RESULT: FAIL $*" >&2
	exit 1
}

mode_request()
{
	dbus-send --system --type=method_call --print-reply \
		--reply-timeout=5000 \
		--dest=com.meego.usb_moded /com/meego/usb_moded \
		com.meego.usb_moded.mode_request 2>/dev/null |
		sed -n 's/.*string "\(.*\)"/\1/p' | tail -n 1
}

set_mode()
{
	dbus-send --system --type=method_call --print-reply \
		--reply-timeout=15000 \
		--dest=com.meego.usb_moded /com/meego/usb_moded \
		com.meego.usb_moded.set_mode "string:$1" >/dev/null 2>&1
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

wait_nm_managed()
{
	count=0
	while [ "$count" -lt 15 ]; do
		[ "$(nmcli -g GENERAL.NM-MANAGED device show usb0 2>/dev/null)" = yes ] &&
			return 0
		count=$((count + 1))
		sleep 1
	done
	return 1
}

restore_host()
{
	set_mode host_mode
	count=0
	while [ "$count" -lt 20 ]; do
		[ "$(role_current)" = host ] && return 0
		count=$((count + 1))
		sleep 1
	done
	printf 'host\n' >"$URS"
	sleep 5
	[ "$(role_current)" = host ]
}

trap 'restore_host >/dev/null 2>&1 || true' EXIT INT TERM

[ "$(role_current)" = host ] || fail "not in host mode before restart soak"
xhci_present || fail "xHCI absent before restart soak"

round=0
while [ "$round" -lt "$CYCLES" ]; do
	round=$((round + 1))
	echo "round=$round restart"
	rc-service usb-signaller restart >/dev/null 2>&1 ||
		fail "usb-signaller restart failed on round $round"

	count=0
	mode=
	while [ "$count" -lt 30 ]; do
		mode=$(mode_request 2>/dev/null || true)
		[ "$mode" = developer_mode ] && break
		count=$((count + 1))
		sleep 1
	done
	[ "$mode" = developer_mode ] ||
		fail "mode_request=$mode after restart on round $round"
	[ -d "$UDC" ] || fail "UDC absent after restart on round $round"

	count=0
	while [ ! -e /sys/class/net/usb0 ] && [ "$count" -lt 15 ]; do
		count=$((count + 1))
		sleep 1
	done
	[ -e /sys/class/net/usb0 ] ||
		fail "usb0 absent after restart on round $round"
	wait_nm_managed ||
		fail "NetworkManager did not manage usb0 after restart on round $round"
	carrier=$(cat /sys/class/net/usb0/carrier 2>/dev/null || true)
	nm_state=$(nmcli -t -f DEVICE,STATE,CONNECTION dev status 2>/dev/null |
		grep '^usb0:' || true)
	if printf '%s\n' "$nm_state" |
		grep -q 'connected:.*Samurai NCM'; then
		fail "NCM active after restart on round $round"
	fi
	echo "round=$round developer=ok carrier=${carrier:-unknown} nm=${nm_state:-missing}"

	set_mode host_mode || fail "set_mode host_mode failed on round $round"
	restore_host || fail "failed to restore host role on round $round"
	sleep 2
	[ "$(role_current)" = host ] ||
		fail "Type-C role is not host after round $round"
	xhci_present || fail "xHCI absent after round $round"
done

echo "RESULT: usb-signaller restart/developer-carrier/host restore passed cycles=$CYCLES"
