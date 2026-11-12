#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
#
# Read-only runtime snapshot for the RMX1931 USB OTG candidate.  It never
# changes a role, writes configfs, mounts storage or touches a block device.

set -u

section()
{
	printf '\n===== %s =====\n' "$*"
}

value()
{
	if [ -e "$1" ]; then
		if data=$(tr '\n' ' ' <"$1" 2>/dev/null); then
			printf '%s\n' "$data"
		else
			printf 'unreadable\n'
		fi
	else
		printf 'missing\n'
	fi
}

section identity
printf 'timestamp='; date -Is
printf 'boot_id='; value /proc/sys/kernel/random/boot_id
printf 'release='; value /proc/sys/kernel/osrelease
printf 'cmdline='; value /proc/cmdline
printf 'uptime='; value /proc/uptime
printf 'tainted='; value /proc/sys/kernel/tainted

section power
printf 'mem_sleep='; value /sys/power/mem_sleep
printf 'suspend_success='; value /sys/power/suspend_stats/success
printf 'suspend_fail='; value /sys/power/suspend_stats/fail

section kernel_config
if [ -r /proc/config.gz ]; then
	gzip -dc /proc/config.gz |
		grep -E '^CONFIG_(USB_DWC3|USB_XHCI|USB_ROLE_SWITCH|REGULATOR_QCOM_USB_VBUS|USB_STORAGE|USB_HID)=' |
		sort
else
	printf '/proc/config.gz missing\n'
fi

section usb_role
found_role=0
for role in /sys/class/usb_role/*; do
	[ -e "$role/role" ] || continue
	found_role=1
	printf 'provider=%s\n' "$(basename "$role")"
	printf 'role='; value "$role/role"
done
[ "$found_role" -ne 0 ] || printf 'no usb_role provider\n'

section dwc3
printf 'udc_state='; value /sys/class/udc/a600000.usb/state
printf 'udc_speed='; value /sys/class/udc/a600000.usb/current_speed
printf 'usb0_carrier='; value /sys/class/net/usb0/carrier
printf 'usb0_operstate='; value /sys/class/net/usb0/operstate
ip -4 -o addr show usb0 2>/dev/null || true

section typec
printf 'port_type='; value /sys/class/typec/port0/port_type
printf 'power_role='; value /sys/class/typec/port0/power_role
printf 'data_role='; value /sys/class/typec/port0/data_role
printf 'orientation='; value /sys/class/typec/port0/orientation
printf 'vconn_source='; value /sys/class/typec/port0/vconn_source
printf 'partner_type='; value /sys/class/typec/port0-partner/type
printf 'partner_pd_revision='; value /sys/class/typec/port0-partner/usb_power_delivery_revision
printf 'platform_wakeup='; value /sys/bus/platform/devices/c440000.spmi:pmic@2:typec@1500/power/wakeup
printf 'platform_wakeup_count='; value /sys/bus/platform/devices/c440000.spmi:pmic@2:typec@1500/power/wakeup_count

section power_supply
for supply in /sys/class/power_supply/*; do
	[ -e "$supply" ] || continue
	name=$(basename "$supply")
	case "$name" in
	*usb*|*mp2650*|*battery*)
		printf '%s.online=' "$name"; value "$supply/online"
		printf '%s.status=' "$name"; value "$supply/status"
		printf '%s.current_now=' "$name"; value "$supply/current_now"
		printf '%s.voltage_now=' "$name"; value "$supply/voltage_now"
		;;
	esac
done

section regulators
for regulator in /sys/class/regulator/*; do
	[ -r "$regulator/name" ] || continue
	regulator_name=$(cat "$regulator/name")
	case "$regulator_name" in
	*usb*|*vbus*|*VBUS*|*USB*)
		printf '%s.name=%s\n' "$(basename "$regulator")" "$regulator_name"
		printf '%s.state=' "$(basename "$regulator")"; value "$regulator/state"
		printf '%s.microvolts=' "$(basename "$regulator")"; value "$regulator/microvolts"
		printf '%s.num_users=' "$(basename "$regulator")"; value "$regulator/num_users"
		;;
	esac
done

section interrupts
grep -E \
	'(^|[[:space:]])(typec|tcpm|attach|cc-state|vbus-change|vconn|try-snk|legacy-cable|PDC|dwc3|spmi)' \
	/proc/interrupts || true

section usb_moded
if command -v dbus-send >/dev/null 2>&1; then
	dbus-send --system --type=method_call --reply-timeout=5000 --print-reply \
		--dest=com.meego.usb_moded /com/meego/usb_moded \
		com.meego.usb_moded.get_modes 2>&1 || true
	dbus-send --system --type=method_call --reply-timeout=5000 --print-reply \
		--dest=com.meego.usb_moded /com/meego/usb_moded \
		com.meego.usb_moded.mode_request 2>&1 || true
else
	printf 'dbus-send missing\n'
fi
if command -v nmcli >/dev/null 2>&1; then
	nmcli dev status 2>&1 || true
fi

section openrc
for service_name in usb-signaller unudhcpd.usb0 samurai-usb-recover; do
	printf '%s=' "$service_name"
	rc-service "$service_name" status 2>&1 || true
done

section boot_guard
if [ -x /usr/sbin/samurai-boot-guard ]; then
	/usr/sbin/samurai-boot-guard status
else
	printf 'boot guard missing\n'
fi

section modules
kernel_release=$(cat /proc/sys/kernel/osrelease)
module_dir=/usr/lib/modules/$kernel_release
printf 'module_dir=%s\n' "$module_dir"
if [ -d "$module_dir" ]; then
	printf 'module_count=%s\n' "$(find "$module_dir" -name '*.ko' | wc -l)"
else
	printf 'module tree missing\n'
fi

section relevant_dmesg
dmesg 2>/dev/null |
	grep -Ei 'typec|tcpm|vbus|usb-role|role-switch|dwc3|xhci|usb-storage|usbhid|configfs-gadget' |
	tail -n 160 || true

section usb_signaller_log
logread 2>/dev/null |
	grep -Ei 'usb-signaller|unudhcpd|networkmanager|usb0|gadget|dwc3' |
	tail -n 80 || true
