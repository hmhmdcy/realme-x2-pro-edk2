#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
#
# Isolate a device-mode enumeration failure from the board's production
# gadget.  The script temporarily stops usb-signaller, binds a minimal
# standard configfs ACM gadget, observes the UDC state, then restores the
# distribution USB stack.  It writes only configfs and a diagnostic log.

set -u

name=samurai-enum-probe
g=/sys/kernel/config/usb_gadget/$name
udc=/sys/class/udc/a600000.usb
log=${SAMURAI_USB_ENUM_PROBE_LOG:-/var/log/samurai/usb-enum-probe.log}
hold=${SAMURAI_USB_ENUM_PROBE_HOLD:-20}
speed=${SAMURAI_USB_ENUM_PROBE_SPEED:-high-speed}
state=missing

log_event()
{
	mkdir -p "${log%/*}"
	printf '%s %s\n' "$(date -Is)" "$*" >>"$log"
}

cleanup_gadget()
{
	if [ -e "$g/UDC" ]; then
		printf '\n' >"$g/UDC" 2>/dev/null || true
	fi
	rm -f "$g/configs/c.1/acm.GS0" 2>/dev/null || true
	rmdir "$g/functions/acm.GS0" 2>/dev/null || true
	rmdir "$g/configs/c.1" 2>/dev/null || true
	rmdir "$g/strings/0x409" 2>/dev/null || true
	rmdir "$g" 2>/dev/null || true
}

restore_service()
{
	cleanup_gadget
	rc-service usb-signaller start >/dev/null 2>&1 || true
	rc-service samurai-usb-recover start >/dev/null 2>&1 || true
	log_event "RESTORE usb_signaller=$(rc-service usb-signaller status 2>&1 | tail -n 1) recover=$(rc-service samurai-usb-recover status 2>&1 | tail -n 1)"
}

trap restore_service EXIT HUP INT TERM

: >"$log"
log_event "BEGIN boot_id=$(cat /proc/sys/kernel/random/boot_id) initial_state=$(cat "$udc/state") speed=$(cat "$udc/current_speed") target_speed=$speed"

rc-service samurai-usb-recover stop >/dev/null 2>&1 || true
rc-service usb-signaller stop >/dev/null 2>&1 || true
rc-service unudhcpd.usb0 stop >/dev/null 2>&1 || true

count=0
while [ -e "$udc/state" ] &&
	[ "$(cat "$udc/state")" != "not attached" ] &&
	[ "$count" -lt 10 ]; do
	count=$((count + 1))
	sleep 1
done

cleanup_gadget
mkdir "$g"
printf '0x1d6b\n' >"$g/idVendor"
printf '0x0104\n' >"$g/idProduct"
printf '0x0200\n' >"$g/bcdUSB"
printf '0x0100\n' >"$g/bcdDevice"
printf '0x02\n' >"$g/bDeviceClass"
printf '0x00\n' >"$g/bDeviceSubClass"
printf '0x00\n' >"$g/bDeviceProtocol"
printf '64\n' >"$g/bMaxPacketSize0"
printf '%s\n' "$speed" >"$g/max_speed"

mkdir "$g/strings/0x409"
printf 'samurai-enum-probe\n' >"$g/strings/0x409/serialnumber"
printf 'EnumProbe ACM\n' >"$g/strings/0x409/product"
printf 'Samurai\n' >"$g/strings/0x409/manufacturer"

mkdir "$g/configs/c.1"
printf '100\n' >"$g/configs/c.1/MaxPower"
mkdir "$g/functions/acm.GS0"
ln -s "$g/functions/acm.GS0" "$g/configs/c.1/acm.GS0"

printf 'a600000.usb\n' >"$g/UDC"
log_event "BOUND udc=$(cat "$g/UDC")"
# A previous diagnostic may have left UDC soft_connect disconnected.  A
# bound gadget alone is not visible to the host until connect is asserted.
printf 'connect\n' >"$udc/soft_connect" 2>/dev/null || true

count=0
configured_seen=0
while [ "$count" -lt 30 ]; do
	state=$(cat "$udc/state" 2>/dev/null || echo missing)
	speed=$(cat "$udc/current_speed" 2>/dev/null || echo missing)
	log_event "STATE t=$count state=$state speed=$speed tty=$([ -e /dev/ttyGS0 ] && echo yes || echo no)"
	[ "$state" = configured ] && configured_seen=1
	[ "$configured_seen" = 1 ] && [ "$state" != configured ] && break
	sleep 1
	count=$((count + 1))
done

if [ "$state" = configured ] && [ "$configured_seen" = 1 ]; then
	log_event "RESULT PASS configured"
else
	log_event "RESULT FAIL state=$state speed=$speed"
fi

sleep "$hold"
log_event "DONE"
[ "$state" = configured ]
