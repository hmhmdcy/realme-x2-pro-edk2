#!/bin/sh
# Offline test for soft-first recovery after an established NCM link loses
# carrier while the UDC remains configured.
set -eu

svc=${1:?usage: test-usb-recover-soft-link-lost.sh SERVICE}
tmp=$(mktemp -d "${TMPDIR:-/tmp}/usb-recover-soft-link.XXXXXX")
helper=

cleanup()
{
	[ -z "$helper" ] || kill "$helper" 2>/dev/null || true
	rm -rf "$tmp"
}
trap cleanup EXIT HUP INT TERM

mkdir -p "$tmp/sys/class/udc/a600000.usb"
mkdir -p "$tmp/sys/class/net/usb0"
mkdir -p "$tmp/sys/class/power_supply/mp2650-input"
mkdir -p "$tmp/sys/bus/platform/drivers/dwc3-qcom"
mkdir -p "$tmp/sys/kernel/config/usb_gadget/usb-signaller-developer"
mkdir -p "$tmp/run" "$tmp/log"
printf '1\n' >"$tmp/run/seen_configured"
printf '1\n' >"$tmp/run/online"
printf '1\n' >"$tmp/run/armed"
printf '0\n' >"$tmp/run/attempts"
printf 'configured' >"$tmp/sys/class/udc/a600000.usb/state"
printf '0' >"$tmp/sys/class/net/usb0/carrier"
printf '1\n' >"$tmp/sys/class/power_supply/mp2650-input/online"
printf 'connect\n' >"$tmp/sys/class/udc/a600000.usb/soft_connect"
: >"$tmp/sys/bus/platform/drivers/dwc3-qcom/unbind"
: >"$tmp/sys/bus/platform/drivers/dwc3-qcom/bind"

(
	while :; do
		if [ "$(cat "$tmp/sys/class/udc/a600000.usb/soft_connect" 2>/dev/null)" = disconnect ]; then
			printf 'disconnect\n' >>"$tmp/soft-connect-events"
			printf 1 >"$tmp/sys/class/net/usb0/carrier"
		fi
		sleep 0.2
	done
) &
helper=$!

SAMURAI_USB_RECOVER_ROOT="$tmp" \
SAMURAI_USB_RECOVER_DBUS=0 \
SAMURAI_USB_RECOVER_INTERVAL=1 \
SAMURAI_USB_RECOVER_GRACE=2 \
SAMURAI_USB_RECOVER_SOFT_GRACE=3 \
SAMURAI_USB_RECOVER_MAX=1 \
SAMURAI_USB_RECOVER_RUN_DIR="$tmp/run" \
SAMURAI_USB_RECOVER_LOG="$tmp/log/recover.log" \
SAMURAI_USB_RECOVER_RESTART_CMD=/bin/true \
	timeout 10 sh "$svc" monitor >/dev/null 2>&1 || true

cat "$tmp/log/recover.log"
for file in "$tmp/run"/*; do
	[ -f "$file" ] || continue
	printf '%s=%s\n' "$(basename "$file")" "$(cat "$file")"
done
printf 'carrier=%s\n' "$(cat "$tmp/sys/class/net/usb0/carrier")"

grep -q 'LINK_LOST state=configured carrier=0' "$tmp/log/recover.log"
grep -q 'SOFT_RECOVER_BEGIN reason=link_lost state=configured carrier=0' \
	"$tmp/log/recover.log"
grep -q 'SOFT_RECOVER_OK reason=link_lost state=configured carrier=1' \
	"$tmp/log/recover.log"
if grep -q ' RECOVER_BEGIN ' "$tmp/log/recover.log"; then
	echo "soft link recovery unexpectedly fell back to full DWC3 rebind" >&2
	exit 1
fi
[ ! -s "$tmp/sys/bus/platform/drivers/dwc3-qcom/unbind" ]
[ "$(cat "$tmp/run/attempts")" = 0 ]
[ "$(cat "$tmp/run/armed")" = 1 ]
grep -q '^disconnect$' "$tmp/soft-connect-events"
[ "$(cat "$tmp/sys/class/udc/a600000.usb/soft_connect")" = connect ]
