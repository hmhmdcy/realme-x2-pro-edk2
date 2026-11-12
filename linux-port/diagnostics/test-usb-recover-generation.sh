#!/bin/sh
# Offline regression for recovery-owned gadget generations.  A watchdog
# rebind must not reset its own retry budget, while a later short host-mode
# transition must still be detected even if the poll loop never observes the
# in-between non-NCM mode.
set -eu

svc=${1:?usage: test-usb-recover-generation.sh SERVICE}
tmp=$(mktemp -d "${TMPDIR:-/tmp}/usb-recover-generation.XXXXXX")
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
mkdir -p "$tmp/bin" "$tmp/run" "$tmp/log" "$gadget"
printf '1\n' >"$tmp/run/seen_configured"
printf '1\n' >"$tmp/run/online"
printf '1\n' >"$tmp/run/armed"
printf '2\n' >"$tmp/run/attempts"
printf 'configured' >"$tmp/sys/class/udc/a600000.usb/state"
printf '0' >"$tmp/sys/class/net/usb0/carrier"
printf '1\n' >"$tmp/sys/class/power_supply/mp2650-input/online"
printf 'connect\n' >"$tmp/sys/class/udc/a600000.usb/soft_connect"
: >"$tmp/sys/bus/platform/drivers/dwc3-qcom/unbind"
: >"$tmp/sys/bus/platform/drivers/dwc3-qcom/bind"

cat >"$tmp/bin/restart.sh" <<EOF
#!/bin/sh
rm -rf "$gadget"
sleep 1
mkdir -p "$gadget"
EOF
chmod 755 "$tmp/bin/restart.sh"

(
	while :; do
		if [ -s "$tmp/sys/bus/platform/drivers/dwc3-qcom/unbind" ]; then
			: >"$tmp/sys/bus/platform/drivers/dwc3-qcom/unbind"
			rm -f "$tmp/sys/class/udc/a600000.usb/state"
			sleep 1
			printf configured >"$tmp/sys/class/udc/a600000.usb/state"
			printf 1 >"$tmp/sys/class/net/usb0/carrier"
		fi
		if [ "$(cat "$tmp/sys/class/udc/a600000.usb/soft_connect")" = disconnect ]; then
			printf 'disconnect\n' >>"$tmp/soft-connect-events"
		fi
		sleep 0.2
	done
) &
helper=$!

(
	sleep 7
	rm -rf "$gadget"
	sleep 0.2
	mkdir -p "$gadget"
) &

SAMURAI_USB_RECOVER_ROOT="$tmp" \
SAMURAI_USB_RECOVER_DBUS=0 \
SAMURAI_USB_RECOVER_INTERVAL=1 \
SAMURAI_USB_RECOVER_GRACE=2 \
SAMURAI_USB_RECOVER_MODE_GRACE=2 \
SAMURAI_USB_RECOVER_REATTACH_GRACE=20 \
SAMURAI_USB_RECOVER_MAX=2 \
SAMURAI_USB_RECOVER_RUN_DIR="$tmp/run" \
SAMURAI_USB_RECOVER_LOG="$tmp/log/recover.log" \
SAMURAI_USB_RECOVER_RESTART_CMD="$tmp/bin/restart.sh" \
	timeout 10 sh "$svc" monitor >/dev/null 2>&1 || true

cat "$tmp/log/recover.log"
for file in "$tmp/run"/*; do
	[ -f "$file" ] || continue
	printf '%s=%s\n' "$(basename "$file")" "$(cat "$file")"
done

grep -q 'BUDGET_RESET reason=mode_transition attempts=2' \
	"$tmp/log/recover.log"
grep -q 'RECOVER_OK attempt=1 reason=link_lost' \
	"$tmp/log/recover.log"
# One reset for the user-visible starting session and one for the later short
# host transition.  A reset caused by the watchdog's own restart would add a
# third entry and make the retry budget unbounded.
[ "$(grep -c 'BUDGET_RESET reason=mode_transition' "$tmp/log/recover.log")" -eq 2 ]
grep -q 'BUDGET_RESET reason=mode_transition attempts=1' \
	"$tmp/log/recover.log"
[ "$(cat "$tmp/run/attempts")" = 0 ]
