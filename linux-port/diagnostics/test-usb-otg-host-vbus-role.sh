#!/bin/sh
# Offline check for the distinction between host data and phone-sourced VBUS.
set -eu

svc=${1:?usage: test-usb-otg-host-vbus-role.sh HOST_PROBE}
tmp=$(mktemp -d "${TMPDIR:-/tmp}/usb-otg-host-vbus.XXXXXX")
trap 'rm -rf "$tmp"' EXIT HUP INT TERM

prepare()
{
	root=$1
	power_role=$2
	data_role=$3
	vbus_state=${4:-disabled}
	otg_en=${5:-00}
	mkdir -p "$root/sys/bus/platform/drivers/xhci-hcd"
	mkdir -p "$root/sys/bus/usb/devices/usb1"
	mkdir -p "$root/sys/class/usb_role/a600000.usb-role-switch"
	mkdir -p "$root/sys/class/typec/port0"
	mkdir -p "$root/sys/class/regulator/regulator.7"
	mkdir -p "$root/sys/kernel/debug/regmap/0-02"
	printf 'host\n' >"$root/sys/class/usb_role/a600000.usb-role-switch/role"
	printf '%s\n' "$power_role" >"$root/sys/class/typec/port0/power_role"
	printf '%s\n' "$data_role" >"$root/sys/class/typec/port0/data_role"
	printf 'normal\n' >"$root/sys/class/typec/port0/orientation"
	printf 'usb_vbus\n' >"$root/sys/class/regulator/regulator.7/name"
	printf '%s\n' "$vbus_state" >"$root/sys/class/regulator/regulator.7/state"
	printf '1100: 00\n1140: %s\n1152: 00\n1153: 20\n' "$otg_en" \
		>"$root/sys/kernel/debug/regmap/0-02/registers"
}

runs()
{
	root=$1
	shift
	SAMURAI_USB_TEST_ROOT="$root" \
	SAMURAI_USB_DMESG=/bin/true \
		sh "$svc" "$@"
}

sink_root=$tmp/sink
prepare "$sink_root" 'source [sink]' 'host [device]'
runs "$sink_root" --allow-no-device >"$tmp/sink-default.log"
grep -q 'typec.port0.power_role=source \[sink\]' "$tmp/sink-default.log"
if runs "$sink_root" --allow-no-device --require-vbus-source \
	>"$tmp/sink-required.log" 2>&1; then
	echo "sink role unexpectedly satisfied --require-vbus-source" >&2
	exit 1
fi
grep -q 'FAIL: Type-C port is not actively sourcing VBUS' \
	"$tmp/sink-required.log"
if runs "$sink_root" --allow-no-device --require-typec-data-role \
	>"$tmp/data-required.log" 2>&1; then
	echo "inactive device data role unexpectedly satisfied --require-typec-data-role" >&2
	exit 1
fi
grep -q 'FAIL: Type-C port is not actively in data host role' \
	"$tmp/data-required.log"

source_root=$tmp/source
prepare "$source_root" '[source] sink' '[host] device' enabled 01
runs "$source_root" --allow-no-device \
	--require-vbus-source --require-typec-data-role \
	>"$tmp/source-required.log"
grep -q 'typec.port0.power_role=\[source\] sink' \
	"$tmp/source-required.log"
grep -q 'typec.port0.data_role=\[host\] device' \
	"$tmp/source-required.log"
grep -q 'typec.vbus_source=active' "$tmp/source-required.log"
grep -q 'typec.data_role_active=host' "$tmp/source-required.log"
grep -q 'regulator.regulator.7.state=enabled' "$tmp/source-required.log"
grep -q 'regulator.usb_vbus.enabled=1' "$tmp/source-required.log"
grep -q 'pmic.8150b.cmd_otg_1140=01' "$tmp/source-required.log"
grep -q 'RESULT: USB2 OTG host probe passed' "$tmp/source-required.log"

source_disabled=$tmp/source-disabled
prepare "$source_disabled" '[source] sink' '[host] device' disabled
if runs "$source_disabled" --allow-no-device \
	--require-vbus-source --require-typec-data-role \
	>"$tmp/source-disabled.log" 2>&1; then
	echo "disabled usb_vbus regulator unexpectedly passed --require-vbus-source" >&2
	exit 1
fi
grep -q 'FAIL: USB VBUS regulator is not enabled while Type-C is a source' \
	"$tmp/source-disabled.log"

echo "RESULT: OTG host VBUS role test passed"
