#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
#
# Read-only USB2 OTG gate for the RMX1931.  Run on the phone after booting the
# dual-role Image/DTB.  It never changes USB roles, VBUS or gadget state.
#
# Optional first argument:
#   device | host | none | any (default: any)

set -u

expected_role=${1:-any}
case "$expected_role" in
device|host|none|any) ;;
*)
	echo "usage: $0 [device|host|none|any]" >&2
	exit 2
	;;
esac

failures=0
config_file=

cleanup()
{
	[ -z "$config_file" ] || rm -f "$config_file"
}
trap cleanup EXIT HUP INT TERM

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

dt_value()
{
	dtb=/proc/device-tree
	node=$1
	prop=$2
	if [ -r "$dtb/$node/$prop" ]; then
		tr '\0' '\n' < "$dtb/$node/$prop" | head -n 1
	else
		echo missing
	fi
}

config_value()
{
	grep -E "^CONFIG_$1=" "$config_file" | tail -n 1 | cut -d= -f2-
}

require_config()
{
	key=$1
	expected=$2
	actual=$(config_value "$key")
	echo "config.$key=$actual"
	[ "$actual" = "$expected" ] ||
		fail "CONFIG_$key=$actual, expected $expected"
}

config_file=$(mktemp) || {
	echo "FAIL: cannot create temporary config file" >&2
	exit 1
}
if [ -r /proc/config.gz ]; then
	gzip -dc /proc/config.gz > "$config_file" ||
		fail "cannot decompress /proc/config.gz"
else
	fail "/proc/config.gz is unavailable; cannot verify the running kernel"
fi

require_config USB_DWC3_DUAL_ROLE y
require_config USB_XHCI_HCD y
require_config USB_XHCI_PLATFORM y
require_config USB_ROLE_SWITCH y
require_config REGULATOR_QCOM_USB_VBUS y
require_config USB_STORAGE y
require_config USB_HID y
if grep -qx 'CONFIG_USB_DWC3_GADGET=y' "$config_file"; then
	fail "CONFIG_USB_DWC3_GADGET is forced on; dual-role metadata is not active"
fi

usb_dt=/soc@0/usb@a600000
typec_dt=/soc@0/spmi@c440000/pmic@2/typec@1500
pm_vbus_dt=/soc@0/spmi@c440000/pmic@2/usb-vbus-regulator@1100
mp2650_dt=/soc@0/geniqup@8c0000/i2c@884000/charger@5c
mp2650_vbus_dt=$mp2650_dt/usb-otg-vbus

dr_mode=$(dt_value "$usb_dt" dr_mode)
default_mode=$(dt_value "$usb_dt" role-switch-default-mode)
echo "dt.usb.dr_mode=$dr_mode"
echo "dt.usb.role_switch_default_mode=$default_mode"
[ "$dr_mode" = otg ] ||
	fail "DT usb dr_mode=$dr_mode, expected otg"
[ "$default_mode" = peripheral ] ||
	fail "DT role-switch-default-mode=$default_mode, expected peripheral"
if [ ! -e "/proc/device-tree/$usb_dt/ports/port@0/endpoint" ]; then
	fail "DWC3 HS endpoint graph is absent"
fi

echo "dt.typec.status=$(dt_value "$typec_dt" status)"
echo "dt.connector.power_role=$(dt_value "$typec_dt/connector" power-role)"
echo "dt.connector.try_power_role=$(dt_value "$typec_dt/connector" try-power-role)"
echo "dt.connector.data_role=$(dt_value "$typec_dt/connector" data-role)"
echo "dt.pm8150b_vbus.status=$(dt_value "$pm_vbus_dt" status)"
if [ -e "/proc/device-tree$mp2650_dt/otg-gpios" ] &&
	[ -d "/proc/device-tree$mp2650_vbus_dt" ]; then
	mp2650_vbus_present=1
	echo "dt.mp2650.otg_gpios=present"
	echo "dt.mp2650.usb_otg_vbus=$(dt_value "$mp2650_vbus_dt" regulator-name)"
else
	mp2650_vbus_present=0
	echo "dt.mp2650.usb_otg_vbus=absent"
fi
[ "$(dt_value "$typec_dt/connector" power-role)" = dual ] ||
	fail "DT connector power-role is not dual"
[ "$(dt_value "$typec_dt/connector" data-role)" = dual ] ||
	fail "DT connector data-role is not dual"
[ "$(dt_value "$typec_dt/connector" try-power-role)" = sink ] ||
	fail "DT connector try-power-role is not sink"
vbus_owner=missing
if [ "$mp2650_vbus_present" -eq 1 ]; then
	vbus_owner=mp2650
elif [ "$(dt_value "$pm_vbus_dt" status)" = okay ]; then
	vbus_owner=pm8150b
else
	fail "no enabled DT VBUS source (expected MP2650 usb-otg-vbus or PM8150B usb-vbus-regulator)"
fi

urss=0
for role in /sys/class/usb_role/*; do
	[ -e "$role" ] || continue
	urss=$((urss + 1))
	name=$(basename "$role")
	role_value=$(value "$role/role")
	echo "usb_role.$name.role=$role_value"
done
[ "$urss" -gt 0 ] ||
	fail "no /sys/class/usb_role provider; DWC3 role-switch did not register"

role_present()
{
	wanted=$1
	for role in /sys/class/usb_role/*; do
		[ -e "$role" ] || continue
		[ "$(value "$role/role")" = "$wanted" ] && return 0
	done
	return 1
}

if [ "$expected_role" != any ] &&
	! role_present "$expected_role"; then
	fail "no USB role-switch reports the requested $expected_role role"
fi

typec_ports=0
for port in /sys/class/typec/port*; do
	[ -e "$port" ] || continue
	name=$(basename "$port")
	case "$name" in
	*-partner) continue ;;
	esac
	typec_ports=$((typec_ports + 1))
	echo "typec.$name.power_role=$(value "$port/power_role")"
	echo "typec.$name.data_role=$(value "$port/data_role")"
	echo "typec.$name.orientation=$(value "$port/orientation")"
done
[ "$typec_ports" -gt 0 ] ||
	fail "no Type-C port is registered"

typec_role_sw_supplier=0
typec_vbus_supplier=0
typec_vbus_supplier_mp2650=0
for link in /sys/class/typec/port0/supplier:*; do
	[ -e "$link" ] || continue
	target=$(readlink -f "$link" 2>/dev/null || echo missing)
	echo "typec.port0.supplier.$(basename "$link")=$target"
	case "$target" in
	*a600000.usb*) typec_role_sw_supplier=1 ;;
	*usb-vbus-regulator*) typec_vbus_supplier=1 ;;
	*0-005c*|*mp2650*) typec_vbus_supplier_mp2650=1 ;;
	esac
done
if [ "$typec_role_sw_supplier" -ne 1 ]; then
	fail "TCPM has no device link to the DWC3 usb-role-switch"
fi
if [ "$vbus_owner" = mp2650 ] && [ "$typec_vbus_supplier_mp2650" -ne 1 ]; then
	fail "TCPM has no device link to the MP2650 usb-otg-vbus regulator"
fi
if [ "$vbus_owner" = pm8150b ] && [ "$typec_vbus_supplier" -ne 1 ]; then
	fail "TCPM has no device link to the PM8150B usb_vbus regulator"
fi

regulator_owner_state=missing
for regulator in /sys/class/regulator/*; do
	[ -r "$regulator/name" ] || continue
	regulator_name=$(cat "$regulator/name")
	case "$regulator_name" in
	mp2650-vbus|usb_vbus)
		echo "regulator.$(basename "$regulator").name=$regulator_name"
		echo "regulator.$(basename "$regulator").state=$(value "$regulator/state")"
		echo "regulator.$(basename "$regulator").num_users=$(value "$regulator/num_users")"
		if [ "$vbus_owner" = mp2650 ] && [ "$regulator_name" = mp2650-vbus ]; then
			regulator_owner_state=$(value "$regulator/state")
		fi
		;;
	esac
done
if [ "$vbus_owner" = mp2650 ] && [ "$regulator_owner_state" = missing ]; then
	fail "MP2650 usb-otg-vbus regulator is not registered"
fi

case "$expected_role" in
device)
	if [ ! -e /sys/class/udc/a600000.usb ]; then
		fail "DWC3 UDC is absent in device role"
	else
		echo "udc.a600000.usb.state=$(value /sys/class/udc/a600000.usb/state)"
		echo "udc.a600000.usb.current_speed=$(value /sys/class/udc/a600000.usb/current_speed)"
	fi
	;;
host)
	if [ ! -e /sys/bus/platform/drivers/xhci-hcd ]; then
		fail "xHCI platform driver directory is absent"
	fi
	if [ -e /sys/class/net/usb0 ]; then
		fail "stale usb0 NCM interface is still present in host role"
	fi
	if command -v nmcli >/dev/null 2>&1 &&
		nmcli -t -f DEVICE,STATE,CONNECTION dev status 2>/dev/null |
		grep -q '^usb0:.*Samurai NCM'; then
		fail "stale Samurai NCM NetworkManager profile is active in host role"
	fi
	root_hubs=
	for hub in /sys/bus/usb/devices/usb*; do
		[ -e "$hub" ] || continue
		root_hubs="$root_hubs $(basename "$hub")"
	done
	if [ -z "$root_hubs" ]; then
		fail "no USB root hub is registered in host role"
	else
		for hub in $root_hubs; do
			echo "host.root_hub=$hub"
		done
	fi
	command -v lsusb >/dev/null 2>&1 && lsusb || true
	command -v lsblk >/dev/null 2>&1 && lsblk -o NAME,TRAN,RM,MODEL || true
	;;
esac

if command -v dbus-send >/dev/null 2>&1; then
	modes=$(dbus-send --system --type=method_call --reply-timeout=5000 --print-reply \
		--dest=com.meego.usb_moded /com/meego/usb_moded \
		com.meego.usb_moded.get_modes 2>/dev/null |
		sed -n 's/.*string "\(.*\)"/\1/p' | tail -n 1)
	echo "usb_moded.get_modes=$modes"
	case ",$modes," in
	*,host_mode,*) ;;
	*) fail "usb-moded does not advertise host_mode" ;;
	esac

	current_mode=$(dbus-send --system --type=method_call --reply-timeout=5000 --print-reply \
		--dest=com.meego.usb_moded /com/meego/usb_moded \
		com.meego.usb_moded.mode_request 2>/dev/null |
		sed -n 's/.*string "\(.*\)"/\1/p' | tail -n 1)
	echo "usb_moded.mode_request=$current_mode"
	if [ "$expected_role" = host ] && [ "$current_mode" != host_mode ]; then
		fail "host role but usb-moded reports $current_mode"
	fi
else
	fail "dbus-send is unavailable; cannot verify the standard pmOS USB stack"
fi

if dmesg 2>/dev/null |
	grep -Eiq \
	'(dwc3|dwc3-qcom|xhci).*(probe.*fail|failed|error|timeout)'; then
	echo "--- relevant dmesg tail ---"
	dmesg | grep -Ei '(dwc3|dwc3-qcom|xhci)' | tail -n 80
	fail "DWC3/xHCI probe or runtime error found in dmesg"
fi

if [ "$failures" -ne 0 ]; then
	echo "RESULT: USB2 OTG baseline check failed ($failures finding(s))" >&2
	exit 1
fi

echo "RESULT: USB2 OTG baseline check passed"
