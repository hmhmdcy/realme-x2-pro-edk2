#!/bin/sh
# Offline state-machine test for host/non-NCM -> Developer mode transitions
# where the controller says configured but the host never raises NCM carrier.
set -eu

svc=${1:?usage: test-usb-recover-mode-transition.sh SERVICE}
tmp=$(mktemp -d "${TMPDIR:-/tmp}/usb-recover-mode-test.XXXXXX")
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
mkdir -p "$tmp/sys/kernel/config/usb_gadget/usb-signaller-mtp"
mkdir -p "$tmp/run" "$tmp/log"
printf '1\n' >"$tmp/run/seen_configured"
printf '1\n' >"$tmp/run/online"
printf '0\n' >"$tmp/run/armed"
printf '2\n' >"$tmp/run/attempts"
printf 'configured' >"$tmp/sys/class/udc/a600000.usb/state"
printf '0' >"$tmp/sys/class/net/usb0/carrier"
printf '1\n' >"$tmp/sys/class/power_supply/mp2650-input/online"
printf 'connect\n' >"$tmp/sys/class/udc/a600000.usb/soft_connect"
: >"$tmp/sys/bus/platform/drivers/dwc3-qcom/unbind"
: >"$tmp/sys/bus/platform/drivers/dwc3-qcom/bind"

(
	while :; do
		if [ -s "$tmp/sys/bus/platform/drivers/dwc3-qcom/unbind" ]; then
			: >"$tmp/sys/bus/platform/drivers/dwc3-qcom/unbind"
			rm -f "$tmp/sys/class/udc/a600000.usb/state"
			sleep 1
			printf configured >"$tmp/sys/class/udc/a600000.usb/state"
			printf 1 >"$tmp/sys/class/net/usb0/carrier"
		fi
		if [ "$(cat "$tmp/sys/class/udc/a600000.usb/soft_connect" 2>/dev/null)" = disconnect ]; then
			printf 'disconnect\n' >>"$tmp/soft-connect-events"
		fi
		sleep 0.2
	done
) &
helper=$!

(
	sleep 1
	mkdir "$tmp/sys/kernel/config/usb_gadget/usb-signaller-developer"
) &

SAMURAI_USB_RECOVER_ROOT="$tmp" \
SAMURAI_USB_RECOVER_DBUS=0 \
SAMURAI_USB_RECOVER_INTERVAL=1 \
SAMURAI_USB_RECOVER_MODE_GRACE=2 \
SAMURAI_USB_RECOVER_REATTACH_GRACE=20 \
SAMURAI_USB_RECOVER_MAX=1 \
SAMURAI_USB_RECOVER_SOFT=0 \
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

grep -q 'MODE_REATTACH mode=developer_mode state=configured' \
	"$tmp/log/recover.log"
grep -q 'BUDGET_RESET reason=mode_transition attempts=2' \
	"$tmp/log/recover.log"
grep -q 'RECOVER_BEGIN attempt=1 reason=mode_transition' \
	"$tmp/log/recover.log"
grep -q 'RECOVER_OK attempt=1 reason=mode_transition' \
	"$tmp/log/recover.log"
[ "$(cat "$tmp/run/armed")" = 1 ]
grep -q '^disconnect$' "$tmp/soft-connect-events"
[ "$(cat "$tmp/sys/class/udc/a600000.usb/soft_connect")" = connect ]
