#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
#
# Synthetic DWC3/xHCI role-switch probe.  It changes the standard usb_role
# sysfs control to host, records the host-side kernel view for a few seconds,
# then always restores device mode.  This does not prove OTG device
# enumeration; a physical OTG device/hub is still required for that.

set -u

cycles=${1:-1}
case $cycles in
''|*[!0-9]*) echo "usage: $0 [cycles]" >&2; exit 2 ;;
esac
[ "$cycles" -ge 1 ] || { echo "usage: $0 [cycles]" >&2; exit 2; }

log=/var/log/samurai/usb-role-switch.log
role_dir=
cleanup_done=0

log_event()
{
	mkdir -p "${log%/*}"
	printf '%s %s\n' "$(date -Is)" "$*" >>"$log"
}

find_role_dir()
{
	for candidate in /sys/class/usb_role/*; do
		[ -e "$candidate/role" ] || continue
		role_dir=$candidate
		return 0
	done
	return 1
}

set_role()
{
	printf '%s\n' "$1" >"$role_dir/role"
}

snapshot()
{
	label=$1
	role=$(cat "$role_dir/role" 2>/dev/null || echo missing)
	udc=$(cat /sys/class/udc/a600000.usb/state 2>/dev/null || echo missing)
	carrier=$(cat /sys/class/net/usb0/carrier 2>/dev/null || echo missing)
	usb_devices=$(ls /sys/bus/usb/devices 2>/dev/null | tr '\n' ' ')
	hosts=$(find /sys/bus/usb/devices -maxdepth 1 -name 'usb[0-9]*' 2>/dev/null |
		tr '\n' ' ')
	log_event "STATE label=$label role=$role udc=$udc carrier=$carrier hosts=${hosts:-none} devices=${usb_devices:-none}"
	command -v lsusb >/dev/null 2>&1 && lsusb >>"$log" || true
}

probe_host_without_external_device()
{
	probe=/root/samurai-tests/test-usb-otg-host.sh
	[ -x "$probe" ] || return 0
	log_event "HOST_PROBE_BEGIN"
	if "$probe" --allow-no-device >>"$log" 2>&1; then
		log_event "HOST_PROBE=PASS"
	else
		log_event "HOST_PROBE=FAIL"
	fi
}

probe_standard_host_baseline()
{
	baseline=/root/samurai-tests/check-usb-otg-baseline.sh
	[ -x "$baseline" ] || return 0
	log_event "HOST_BASELINE_BEGIN"
	if "$baseline" host >>"$log" 2>&1; then
		log_event "HOST_BASELINE=PASS"
	else
		log_event "HOST_BASELINE=FAIL"
	fi
}

restore_device()
{
	if [ -n "$role_dir" ] && [ "$(cat "$role_dir/role" 2>/dev/null || echo missing)" != device ]; then
		log_event "RESTORE device"
		set_role device || true
	fi
	sleep 5
	dbus-send --system --type=method_call --reply-timeout=5000 --print-reply \
		--dest=com.meego.usb_moded /com/meego/usb_moded \
		com.meego.usb_moded.set_mode "string:developer_mode" >/dev/null 2>&1 || true
	sleep 15
	mode=$(dbus-send --system --type=method_call --reply-timeout=5000 --print-reply \
		--dest=com.meego.usb_moded /com/meego/usb_moded \
		com.meego.usb_moded.mode_request 2>/dev/null |
		sed -n 's/.*string "\(.*\)"/\1/p' | tail -n 1)
	udc=$(cat /sys/class/udc/a600000.usb/state 2>/dev/null || echo missing)
	carrier=$(cat /sys/class/net/usb0/carrier 2>/dev/null || echo missing)
	log_event "RESTORE_RESULT mode=${mode:-missing} udc=$udc carrier=$carrier"
}

cleanup()
{
	[ "$cleanup_done" -eq 0 ] || return 0
	cleanup_done=1
	restore_device
	log_event "END"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM

mkdir -p "${log%/*}"
log_event "BEGIN boot_id=$(cat /proc/sys/kernel/random/boot_id)"
if ! find_role_dir; then
	log_event "FAIL no usb_role provider"
	exit 1
fi
snapshot initial

cycle=1
while [ "$cycle" -le "$cycles" ]; do
	log_event "CYCLE_BEGIN cycle=$cycle"
	log_event "SWITCH host cycle=$cycle"
	set_role host
	sleep 5
	snapshot "host-$cycle"
	probe_host_without_external_device
	probe_standard_host_baseline
	sleep 8
	log_event "SWITCH device cycle=$cycle"
	set_role device
	sleep 5
	snapshot "restored-$cycle"
	log_event "CYCLE_END cycle=$cycle"
	cycle=$((cycle + 1))
done

exit 0
