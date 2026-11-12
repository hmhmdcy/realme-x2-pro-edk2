#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
#
# Capture DWC3/gadget trace events around a public UDC soft reconnect.
# This distinguishes a host that resets but never sends a control request
# from a gadget that receives GET_DESCRIPTOR and fails later.

set -u

tr=/sys/kernel/tracing
out=${SAMURAI_USB_ENUM_TRACE_LOG:-/var/log/samurai/usb-enum-trace.log}
udc=/sys/class/udc/a600000.usb
duration=${SAMURAI_USB_ENUM_TRACE_SECONDS:-10}

log()
{
	mkdir -p "${out%/*}"
	printf '%s %s\n' "$(date -Is)" "$*" >>"$out"
}

disable_events()
{
	for event in \
		dwc3/dwc3_ctrl_req \
		dwc3/dwc3_event \
		gadget/usb_gadget_set_state \
		gadget/usb_gadget_connect \
		gadget/usb_gadget_disconnect \
		gadget/usb_gadget_vbus_connect \
		gadget/usb_gadget_vbus_disconnect; do
		[ ! -e "$tr/events/$event/enable" ] ||
			echo 0 >"$tr/events/$event/enable" 2>/dev/null || true
	done
}

restore_soft_connect()
{
	# soft_connect is write-only.  A failed or interrupted trace must never
	# leave the UDC electrically disconnected: the host then reports a
	# connected-but-never-enumerating port until the next manual reconnect.
	[ -e "$udc/soft_connect" ] || return 0
	printf 'connect\n' >"$udc/soft_connect" 2>/dev/null || true
}

cleanup()
{
	echo 0 >"$tr/tracing_on" 2>/dev/null || true
	disable_events
	restore_soft_connect
	rc-service samurai-usb-recover start >/dev/null 2>&1 || true
}

trap cleanup EXIT HUP INT TERM

: >"$out"
rc-service samurai-usb-recover stop >/dev/null 2>&1 || true

echo 0 >"$tr/tracing_on" 2>/dev/null || true
: >"$tr/trace" 2>/dev/null || true
disable_events
for event in \
	dwc3/dwc3_ctrl_req \
	dwc3/dwc3_event \
	gadget/usb_gadget_set_state \
	gadget/usb_gadget_connect \
	gadget/usb_gadget_disconnect \
	gadget/usb_gadget_vbus_connect \
	gadget/usb_gadget_vbus_disconnect; do
	echo 1 >"$tr/events/$event/enable" 2>/dev/null || true
done

log "BEGIN boot_id=$(cat /proc/sys/kernel/random/boot_id) state=$(cat "$udc/state") speed=$(cat "$udc/current_speed")"
echo 1 >"$tr/tracing_on" 2>/dev/null || true
echo disconnect >"$udc/soft_connect" 2>/dev/null || true
sleep 1
restore_soft_connect
sleep "$duration"
echo 0 >"$tr/tracing_on" 2>/dev/null || true

log "END state=$(cat "$udc/state") speed=$(cat "$udc/current_speed")"
log "TRACE_FOLLOWS"
cat "$tr/trace" >>"$out" 2>/dev/null || true
ctrl_count=$(grep -c 'dwc3_ctrl_req' "$out" 2>/dev/null || true)
event_count=$(grep -c 'dwc3_event' "$out" 2>/dev/null || true)
log "COUNTS ctrl_req=$ctrl_count dwc3_event=$event_count"
disable_events
restore_soft_connect
grep -E 'dwc3_ctrl_req|dwc3_event|COUNTS|BEGIN|END' "$out" | tail -n 80
