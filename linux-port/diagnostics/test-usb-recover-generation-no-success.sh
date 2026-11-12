#!/bin/sh
# Offline regression: recovery-owned gadget generations must not reset the
# retry budget before the current cable session has ever enumerated.
set -eu

svc=${1:?usage: test-usb-recover-generation-no-success.sh SERVICE}
tmp=$(mktemp -d "${TMPDIR:-/tmp}/usb-recover-generation-no-success.XXXXXX")
cleanup()
{
	rm -rf "$tmp"
}
trap cleanup EXIT HUP INT TERM

mkdir -p "$tmp/sys/class/udc/a600000.usb"
mkdir -p "$tmp/sys/class/net/usb0"
mkdir -p "$tmp/sys/class/power_supply/mp2650-input"
mkdir -p "$tmp/sys/bus/platform/drivers/dwc3-qcom"
mkdir -p "$tmp/sys/kernel/config/usb_gadget/usb-signaller-developer"
mkdir -p "$tmp/run" "$tmp/log"
printf '0\n' >"$tmp/run/seen_configured"
printf '1\n' >"$tmp/run/online"
printf '0\n' >"$tmp/run/armed"
printf '2\n' >"$tmp/run/attempts"
printf 'default' >"$tmp/sys/class/udc/a600000.usb/state"
printf 'high-speed' >"$tmp/sys/class/udc/a600000.usb/current_speed"
printf '0' >"$tmp/sys/class/net/usb0/carrier"
printf '1\n' >"$tmp/sys/class/power_supply/mp2650-input/online"
printf 'connect\n' >"$tmp/sys/class/udc/a600000.usb/soft_connect"
: >"$tmp/sys/bus/platform/drivers/dwc3-qcom/unbind"
: >"$tmp/sys/bus/platform/drivers/dwc3-qcom/bind"

SAMURAI_USB_RECOVER_ROOT="$tmp" \
SAMURAI_USB_RECOVER_DBUS=0 \
SAMURAI_USB_RECOVER_INTERVAL=1 \
SAMURAI_USB_RECOVER_ENUM_GRACE=2 \
SAMURAI_USB_RECOVER_MAX=2 \
SAMURAI_USB_RECOVER_RUN_DIR="$tmp/run" \
SAMURAI_USB_RECOVER_LOG="$tmp/log/recover.log" \
SAMURAI_USB_RECOVER_RESTART_CMD=/bin/true \
	timeout 5 sh "$svc" monitor >/dev/null 2>&1 || true

cat "$tmp/log/recover.log"
[ "$(cat "$tmp/run/attempts")" = 2 ]
grep -q 'BUDGET_KEEP reason=no_configured attempts=2' "$tmp/log/recover.log"
if grep -q 'BUDGET_RESET reason=mode_transition' "$tmp/log/recover.log"; then
	echo "budget reset before any successful enumeration" >&2
	exit 1
fi
