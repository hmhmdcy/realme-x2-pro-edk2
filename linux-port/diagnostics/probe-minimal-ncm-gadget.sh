#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
#
# Isolate the standard configfs NCM function from usb-signaller and the
# board recovery service.  This answers whether a clean, single-function
# NCM gadget enumerates at a given link speed before touching the
# production gadget stack.

set -u

name=${SAMURAI_USB_NCM_PROBE_NAME:-samurai-ncm-probe}
g=/sys/kernel/config/usb_gadget/$name
udc=/sys/class/udc/a600000.usb
log=${SAMURAI_USB_NCM_PROBE_LOG:-/var/log/samurai/usb-ncm-probe.log}
hold=${SAMURAI_USB_NCM_PROBE_HOLD:-20}
speed=${SAMURAI_USB_NCM_PROBE_SPEED:-high-speed}
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
	rm -f "$g/configs/c.1/ncm.usb0" 2>/dev/null || true
	rmdir "$g/functions/ncm.usb0" 2>/dev/null || true
	rmdir "$g/configs/c.1/strings/0x409" 2>/dev/null || true
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
printf '0x0525\n' >"$g/idVendor"
printf '0xa4a1\n' >"$g/idProduct"
printf '0x0201\n' >"$g/bcdUSB"
printf '0x0100\n' >"$g/bcdDevice"
printf '0xef\n' >"$g/bDeviceClass"
printf '0x02\n' >"$g/bDeviceSubClass"
printf '0x01\n' >"$g/bDeviceProtocol"
printf '64\n' >"$g/bMaxPacketSize0"
printf '%s\n' "$speed" >"$g/max_speed"

mkdir "$g/strings/0x409"
printf 'samurai-ncm-probe\n' >"$g/strings/0x409/serialnumber"
printf 'SamuraiNCM Probe\n' >"$g/strings/0x409/product"
printf 'Samurai\n' >"$g/strings/0x409/manufacturer"

mkdir "$g/configs/c.1"
printf '500\n' >"$g/configs/c.1/MaxPower"
printf '0x80\n' >"$g/configs/c.1/bmAttributes"
mkdir "$g/configs/c.1/strings/0x409"
printf 'Samurai NCM Probe\n' >"$g/configs/c.1/strings/0x409/configuration"
mkdir "$g/functions/ncm.usb0"
ln -s "$g/functions/ncm.usb0" "$g/configs/c.1/ncm.usb0"

printf 'a600000.usb\n' >"$g/UDC"
log_event "BOUND udc=$(cat "$g/UDC") ifname=$(cat "$g/functions/ncm.usb0/ifname" 2>/dev/null)"
# Bind alone does not guarantee a D+ pull-up after a prior diagnostic used
# the UDC soft_connect control.
printf 'connect\n' >"$udc/soft_connect" 2>/dev/null || true

count=0
configured_seen=0
while [ "$count" -lt 30 ]; do
	state=$(cat "$udc/state" 2>/dev/null || echo missing)
	speed=$(cat "$udc/current_speed" 2>/dev/null || echo missing)
	log_event "STATE t=$count state=$state speed=$speed carrier=$(cat /sys/class/net/usb0/carrier 2>/dev/null || echo missing)"
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
log_event "DONE state=$(cat "$udc/state" 2>/dev/null) speed=$(cat "$udc/current_speed" 2>/dev/null)"
[ "$configured_seen" = 1 ]
