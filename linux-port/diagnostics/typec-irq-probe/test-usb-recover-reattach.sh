#!/bin/sh
# Offline state-machine test for the VBUS-on reattach recovery path.
set -eu

svc=${1:?usage: test-usb-recover-reattach.sh SERVICE}
tmp=$(mktemp -d "${TMPDIR:-/tmp}/usb-recover-test.XXXXXX")
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
mkdir -p "$tmp/run" "$tmp/log"
printf '1\n' >"$tmp/run/seen_configured"
printf 'not attached' >"$tmp/sys/class/udc/a600000.usb/state"
printf '0' >"$tmp/sys/class/net/usb0/carrier"
printf '0' >"$tmp/sys/class/power_supply/mp2650-input/online"
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
		sleep 0.2
	done
) &
helper=$!

(
	sleep 1
	printf 1 >"$tmp/sys/class/power_supply/mp2650-input/online"
) &

SAMURAI_USB_RECOVER_ROOT="$tmp" \
SAMURAI_USB_RECOVER_INTERVAL=1 \
SAMURAI_USB_RECOVER_REATTACH_GRACE=2 \
SAMURAI_USB_RECOVER_MAX=1 \
SAMURAI_USB_RECOVER_RUN_DIR="$tmp/run" \
SAMURAI_USB_RECOVER_LOG="$tmp/log/recover.log" \
SAMURAI_USB_RECOVER_RESTART_CMD=/bin/true \
	timeout 9 sh "$svc" monitor >/dev/null 2>&1 || true

cat "$tmp/log/recover.log"
for file in "$tmp/run"/*; do
	[ -f "$file" ] || continue
	printf '%s=%s\n' "$(basename "$file")" "$(cat "$file")"
done
printf 'carrier=%s\n' "$(cat "$tmp/sys/class/net/usb0/carrier")"

grep -q 'VBUS_ON seen=1' "$tmp/log/recover.log"
grep -q 'reason=reattach' "$tmp/log/recover.log"
grep -q 'RECOVER_OK attempt=1 reason=reattach' "$tmp/log/recover.log"
[ "$(cat "$tmp/run/armed")" = 1 ]
