#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
#
# Read-only host-role probe for the RMX1931 OTG candidate.
# Run while a USB-C OTG adapter/dock is connected.  It does not mount disks,
# change roles or write configfs.
#
# Usage:
#   test-usb-otg-host.sh [--storage] [--hid] [--allow-no-device]
#                         [--require-vbus-source] [--require-typec-data-role]

set -u

root=${SAMURAI_USB_TEST_ROOT:-}
dmesg_cmd=${SAMURAI_USB_DMESG:-dmesg}
require_storage=0
require_hid=0
allow_no_device=0
require_vbus_source=0
require_typec_data_role=0

for argument in "$@"; do
	case "$argument" in
	--storage) require_storage=1 ;;
	--hid) require_hid=1 ;;
	--allow-no-device) allow_no_device=1 ;;
	--require-vbus-source) require_vbus_source=1 ;;
	--require-typec-data-role) require_typec_data_role=1 ;;
	*)
		echo "usage: $0 [--storage] [--hid] [--allow-no-device] [--require-vbus-source] [--require-typec-data-role]" >&2
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
	if [ -r "$root$1" ]; then
		cat "$root$1"
	else
		echo missing
	fi
}

find_vbus_regulator()
{
	for regulator in "$root"/sys/class/regulator/regulator.*; do
		[ -e "$regulator" ] || continue
		case $(value "/sys/class/regulator/${regulator##*/}/name") in
		usb_vbus|mp2650-vbus)
			printf '%s\n' "${regulator##*/}"
			return 0
			;;
		esac
	done
	return 1
}

read_pmic_reg()
{
	register=$1
	registers="$root/sys/kernel/debug/regmap/0-02/registers"
	[ -r "$registers" ] || return 1
	awk -v reg="$register" '
		$1 == reg ":" { print $2; found = 1; exit }
		END { if (!found) exit 1 }
	' "$registers"
}

role_count=0
for role in "$root"/sys/class/usb_role/*; do
	[ -e "$role" ] || continue
	role_name=$(basename "$role")
	role_value=$(value "/sys/class/usb_role/$role_name/role")
	echo "usb_role.$role_name.role=$role_value"
	[ "$role_value" = host ] && role_count=$((role_count + 1))
done
[ "$role_count" -gt 0 ] ||
	fail "no USB role-switch reports host role"

typec_power_role=$(value /sys/class/typec/port0/power_role)
typec_data_role=$(value /sys/class/typec/port0/data_role)
typec_orientation=$(value /sys/class/typec/port0/orientation)
echo "typec.port0.power_role=$typec_power_role"
echo "typec.port0.data_role=$typec_data_role"
echo "typec.port0.orientation=$typec_orientation"
vbus_regulator=
if find_vbus_regulator >/dev/null; then
	vbus_regulator=$(find_vbus_regulator)
	vbus_state=$(value "/sys/class/regulator/$vbus_regulator/state")
	vbus_name=$(value "/sys/class/regulator/$vbus_regulator/name")
	echo "regulator.$vbus_regulator.name=$vbus_name"
	echo "regulator.$vbus_regulator.state=$vbus_state"
else
	vbus_state=missing
	vbus_name=missing
	echo "regulator.vbus=missing"
fi
if [ "$require_typec_data_role" -eq 1 ]; then
	case $typec_data_role in
	*'[host]'*) echo "typec.data_role_active=host" ;;
	*) fail "Type-C port is not actively in data host role" ;;
	esac
fi
if [ "$require_vbus_source" -eq 1 ]; then
	case $typec_power_role in
	*'[source]'*) echo "typec.vbus_source=active" ;;
	*) fail "Type-C port is not actively sourcing VBUS" ;;
	esac
	case $vbus_state in
	enabled*) echo "regulator.$vbus_name.enabled=1" ;;
	*) fail "USB VBUS regulator is not enabled while Type-C is a source" ;;
	esac

	if read_pmic_reg 1140 >/dev/null 2>&1; then
		cmd_otg=$(read_pmic_reg 1140)
		otg_cfg=$(read_pmic_reg 1153)
		otg_cl=$(read_pmic_reg 1152)
		echo "pmic.8150b.cmd_otg_1140=$cmd_otg"
		echo "pmic.8150b.otg_cfg_1153=$otg_cfg"
		echo "pmic.8150b.otg_current_limit_1152=$otg_cl"
		case $cmd_otg in
		[0-9a-fA-F][0-9a-fA-F]) ;;
		*)
			fail "PM8150B CMD_OTG register is not readable"
			cmd_otg=
			;;
		esac
		case $otg_cfg in
		[0-9a-fA-F][0-9a-fA-F]) ;;
		*)
			fail "PM8150B OTG_CFG register is not readable"
			otg_cfg=
			;;
		esac
		if [ "$vbus_name" = mp2650-vbus ]; then
			if [ -n "$cmd_otg" ] && [ $((0x$cmd_otg & 1)) -ne 0 ]; then
				fail "PM8150B OTG_EN must stay clear when MP2650 owns VBUS"
			fi
			echo "pmic.8150b.otg_en=clear"
		else
			if [ -n "$cmd_otg" ] && [ $((0x$cmd_otg & 1)) -ne 1 ]; then
				fail "PM8150B OTG_EN bit is not set while TCPM is a source"
			fi
			if [ -n "$otg_cfg" ] && [ $((0x$otg_cfg & 2)) -ne 0 ]; then
				fail "PM8150B OTG_EN_SRC_CFG must stay clear so software owns OTG enable"
			fi
		fi
	else
		[ "$vbus_name" = mp2650-vbus ] ||
			fail "PM8150B SPMI regmap is unavailable; cannot verify hardware OTG enable"
	fi
fi

if [ ! -e "$root/sys/bus/platform/drivers/xhci-hcd" ]; then
	fail "xHCI platform driver is not registered"
fi

root_hubs=0
external_devices=0
for device in "$root"/sys/bus/usb/devices/*; do
	[ -e "$device" ] || continue
	name=$(basename "$device")
	case "$name" in
	usb*)
		case "$name" in
		*-*) ;;
		*)
			root_hubs=$((root_hubs + 1))
			echo "root_hub.$name.speed=$(value "/sys/bus/usb/devices/$name/speed")"
			continue
			;;
		esac
		;;
	esac
	[ -r "$device/idVendor" ] || continue
	external_devices=$((external_devices + 1))
	echo "device.$name.idVendor=$(value "/sys/bus/usb/devices/$name/idVendor")"
	echo "device.$name.idProduct=$(value "/sys/bus/usb/devices/$name/idProduct")"
	echo "device.$name.manufacturer=$(value "/sys/bus/usb/devices/$name/manufacturer")"
	echo "device.$name.product=$(value "/sys/bus/usb/devices/$name/product")"
	echo "device.$name.speed=$(value "/sys/bus/usb/devices/$name/speed")"
done

[ "$root_hubs" -gt 0 ] ||
	fail "no USB root hub is registered"
if [ "$external_devices" -eq 0 ] && [ "$allow_no_device" -ne 1 ]; then
	fail "host role has no enumerated external USB device"
fi

command -v lsusb >/dev/null 2>&1 && lsusb || true
if command -v lsblk >/dev/null 2>&1; then
	lsblk -o NAME,TRAN,RM,SIZE,MODEL,MOUNTPOINTS |
		awk 'NR == 1 || $2 == "usb"'
fi

if [ "$require_storage" -eq 1 ]; then
	if command -v lsblk >/dev/null 2>&1 &&
		lsblk -dn -o TRAN 2>/dev/null | grep -qx usb; then
		echo "storage.usb_transport=present"
	else
		fail "no USB mass-storage block device is visible"
	fi
fi

if [ "$require_hid" -eq 1 ]; then
	if [ -d "$root/sys/bus/usb/drivers/usbhid" ]; then
		hid_bindings=0
		for binding in "$root"/sys/bus/usb/drivers/usbhid/*; do
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

if "$dmesg_cmd" 2>/dev/null |
	grep -Eiq \
	'(usb [0-9-]+.*(device descriptor read|unable to enumerate|error -|not accepting address))'; then
	echo "--- relevant dmesg tail ---"
	"$dmesg_cmd" | grep -Ei 'usb|xhci' | tail -n 80
	fail "USB enumeration error found in dmesg"
fi

if [ "$failures" -ne 0 ]; then
	echo "RESULT: USB2 OTG host probe failed ($failures finding(s))" >&2
	exit 1
fi

echo "RESULT: USB2 OTG host probe passed"
