#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
#
# Read-only host-role probe for the RMX1931 OTG candidate.
# Run while a USB-C OTG adapter/dock is connected.  It does not mount disks,
# change roles or write configfs.
#
# Usage:
#   test-usb-otg-host.sh [--storage] [--hid] [--allow-no-device]

set -u

require_storage=0
require_hid=0
allow_no_device=0

for argument in "$@"; do
	case "$argument" in
	--storage) require_storage=1 ;;
	--hid) require_hid=1 ;;
	--allow-no-device) allow_no_device=1 ;;
	*)
		echo "usage: $0 [--storage] [--hid] [--allow-no-device]" >&2
		exit 2
		;;
	esac
done

failures=0

fail()
{
	echo "FAIL: $*" >&2
	failures=$((failures + 1))
}

value()
{
	if [ -r "$1" ]; then
		cat "$1"
	else
		echo missing
	fi
}

role_count=0
for role in /sys/class/usb_role/*; do
	[ -e "$role" ] || continue
	role_value=$(value "$role/role")
	echo "usb_role.$(basename "$role").role=$role_value"
	[ "$role_value" = host ] && role_count=$((role_count + 1))
done
[ "$role_count" -gt 0 ] ||
	fail "no USB role-switch reports host role"

if [ ! -e /sys/bus/platform/drivers/xhci-hcd ]; then
	fail "xHCI platform driver is not registered"
fi

root_hubs=0
external_devices=0
for device in /sys/bus/usb/devices/*; do
	[ -e "$device" ] || continue
	name=$(basename "$device")
	case "$name" in
	usb*)
		case "$name" in
		*-*) ;;
		*)
			root_hubs=$((root_hubs + 1))
			echo "root_hub.$name.speed=$(value "$device/speed")"
			continue
			;;
		esac
		;;
	esac
	[ -r "$device/idVendor" ] || continue
	external_devices=$((external_devices + 1))
	echo "device.$name.idVendor=$(value "$device/idVendor")"
	echo "device.$name.idProduct=$(value "$device/idProduct")"
	echo "device.$name.manufacturer=$(value "$device/manufacturer")"
	echo "device.$name.product=$(value "$device/product")"
	echo "device.$name.speed=$(value "$device/speed")"
done

[ "$root_hubs" -gt 0 ] ||
	fail "no USB root hub is registered"
if [ "$external_devices" -eq 0 ] && [ "$allow_no_device" -ne 1 ]; then
	fail "host role has no enumerated external USB device"
fi

command -v lsusb >/dev/null 2>&1 && lsusb || true
command -v lsblk >/dev/null 2>&1 &&
	lsblk -o NAME,TRAN,RM,SIZE,MODEL,MOUNTPOINTS || true

if [ "$require_storage" -eq 1 ]; then
	if command -v lsblk >/dev/null 2>&1 &&
		lsblk -dn -o TRAN 2>/dev/null | grep -qx usb; then
		echo "storage.usb_transport=present"
	else
		fail "no USB mass-storage block device is visible"
	fi
fi

if [ "$require_hid" -eq 1 ]; then
	if [ -d /sys/bus/usb/drivers/usbhid ]; then
		hid_bindings=0
		for binding in /sys/bus/usb/drivers/usbhid/*; do
			[ -e "$binding" ] || continue
			case "$(basename "$binding")" in
			bind|unbind|module) continue ;;
			esac
			hid_bindings=$((hid_bindings + 1))
			echo "hid.binding=$(basename "$binding")"
		done
		[ "$hid_bindings" -gt 0 ] ||
			fail "USB HID driver has no bound interface"
	else
		fail "USB HID driver directory is absent"
	fi
fi

if dmesg 2>/dev/null |
	grep -Eiq \
	'(usb [0-9-]+.*(device descriptor read|unable to enumerate|error -|not accepting address))'; then
	echo "--- relevant dmesg tail ---"
	dmesg | grep -Ei 'usb|xhci' | tail -n 80
	fail "USB enumeration error found in dmesg"
fi

if [ "$failures" -ne 0 ]; then
	echo "RESULT: USB2 OTG host probe failed ($failures finding(s))" >&2
	exit 1
fi

echo "RESULT: USB2 OTG host probe passed"
