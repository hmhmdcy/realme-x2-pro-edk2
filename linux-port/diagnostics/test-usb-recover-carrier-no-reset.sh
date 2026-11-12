#!/bin/sh
# Offline regression: a configured UDC with NCM carrier 0 must not trigger
# a soft reconnect or a DWC3 rebind.  Carrier is a network-layer property;
# Windows can legitimately leave the NCM data interface at alt 0 while idle.
set -eu

svc=${1:?usage: test-usb-recover-carrier-no-reset.sh SERVICE}
tmp=$(mktemp -d "${TMPDIR:-/tmp}/usb-recover-carrier.XXXXXX")
helper=

cleanup()
{
	[ -z "$helper" ] || kill "$helper" 2>/dev/null || true
	rm -rf "$tmp"
}
trap cleanup EXIT HUP INT TERM

gadget=$tmp/sys/kernel/config/usb_gadget/usb-signaller-developer
mkdir -p "$tmp/sys/class/udc/a600000.usb"
mkdir -p "$tmp/sys/class/net/usb0"
mkdir -p "$tmp/sys/class/power_supply/mp2650-input"
mkdir -p "$tmp/sys/bus/platform/drivers/dwc3-qcom"
mkdir -p "$tmp/run" "$tmp/log" "$gadget"
printf '1\n' >"$tmp/run/seen_configured"
printf '1\n' >"$tmp/run/online"
printf '1\n' >"$tmp/run/armed"
printf '2\n' >"$tmp/run/attempts"
printf 'configured' >"$tmp/sys/class/udc/a600000.usb/state"
printf 'high-speed' >"$tmp/sys/class/udc/a600000.usb/current_speed"
printf '0' >"$tmp/sys/class/net/usb0/carrier"
printf '1\n' >"$tmp/sys/class/power_supply/mp2650-input/online"
printf 'connect\n' >"$tmp/sys/class/udc/a600000.usb/soft_connect"
: >"$tmp/sys/bus/platform/drivers/dwc3-qcom/unbind"
: >"$tmp/sys/bus/platform/drivers/dwc3-qcom/bind"

(
	while :; do
		if [ "$(cat "$tmp/sys/class/udc/a600000.usb/soft_connect" 2>/dev/null)" = disconnect ]; then
			printf 'disconnect\n' >>"$tmp/soft-connect-events"
		fi
		sleep 0.2
	done
) &
helper=$!

(
	sleep 2
	rm -rf "$gadget"
	sleep 0.2
	mkdir -p "$gadget"
) &

SAMURAI_USB_RECOVER_ROOT="$tmp" \
SAMURAI_USB_RECOVER_DBUS=0 \
SAMURAI_USB_RECOVER_INTERVAL=1 \
SAMURAI_USB_RECOVER_ENUM_GRACE=2 \
SAMURAI_USB_RECOVER_MAX=2 \
SAMURAI_USB_RECOVER_RUN_DIR="$tmp/run" \
SAMURAI_USB_RECOVER_LOG="$tmp/log/recover.log" \
SAMURAI_USB_RECOVER_RESTART_CMD=/bin/true \
	timeout 8 sh "$svc" monitor >/dev/null 2>&1 || true

if [ -e "$tmp/log/recover.log" ]; then
	cat "$tmp/log/recover.log"
fi
for file in "$tmp/run"/*; do
	[ -f "$file" ] || continue
	printf '%s=%s\n' "$(basename "$file")" "$(cat "$file")"
done
printf 'carrier=%s\n' "$(cat "$tmp/sys/class/net/usb0/carrier")"

if [ -e "$tmp/log/recover.log" ]; then
	! grep -Eq 'SOFT_RECOVER_BEGIN|SOFT_RECOVER_OK|RECOVER_BEGIN|LINK_LOST|MODE_REATTACH' \
		"$tmp/log/recover.log"
	grep -q 'BUDGET_KEEP reason=mode_transition attempts=2' \
		"$tmp/log/recover.log"
fi
[ ! -s "$tmp/sys/bus/platform/drivers/dwc3-qcom/unbind" ]
[ "$(cat "$tmp/run/attempts")" = 2 ]
[ "$(cat "$tmp/run/armed")" = 1 ]
[ "$(cat "$tmp/run/seen_configured")" = 1 ]
[ ! -e "$tmp/soft-connect-events" ] || [ ! -s "$tmp/soft-connect-events" ]
[ "$(cat "$tmp/sys/class/udc/a600000.usb/soft_connect")" = connect ]
