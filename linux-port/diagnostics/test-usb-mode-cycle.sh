#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
#
# Exercise the standard postmarketOS usb-moded device modes and always return
# to Developer mode.  Run from the phone locally or in a nohup background
# process; do not rely on the SSH connection surviving a mode change.

set -u

dwell=${1:-15}
log=/var/log/samurai/usb-mode-cycle.log
failures=0

log_event()
{
	mkdir -p "${log%/*}"
	printf '%s %s\n' "$(date -Is)" "$*" >>"$log"
}

request_mode()
{
	wanted=$1
	log_event "REQUEST mode=$wanted"
	dbus-send --system --type=method_call --reply-timeout=5000 --print-reply \
		--dest=com.meego.usb_moded /com/meego/usb_moded \
		com.meego.usb_moded.set_mode "string:$wanted" >/dev/null 2>&1
}

current_mode()
{
	dbus-send --system --type=method_call --reply-timeout=5000 --print-reply \
		--dest=com.meego.usb_moded /com/meego/usb_moded \
		com.meego.usb_moded.mode_request 2>/dev/null |
		sed -n 's/.*string "\(.*\)"/\1/p' | tail -n 1
}

snapshot()
{
	state=$(cat /sys/class/udc/a600000.usb/state 2>/dev/null || echo missing)
	carrier=$(cat /sys/class/net/usb0/carrier 2>/dev/null || echo missing)
	addr=$(ip -4 -o addr show usb0 2>/dev/null | awk '{print $4}')
	power=$(tr '\n' ' ' < /sys/class/typec/port0/power_role 2>/dev/null)
	data=$(tr '\n' ' ' < /sys/class/typec/port0/data_role 2>/dev/null)
	log_event "STATE udc=$state carrier=$carrier addr=${addr:-missing} power=$power data=$data"
}

restore_developer()
{
	request_mode developer_mode
	sleep 20
	mode=$(current_mode)
	if [ "$mode" != developer_mode ]; then
		log_event "RESTORE_RETRY mode=$mode"
		rc-service usb-signaller-developer-mode restart >/dev/null 2>&1 || true
		request_mode developer_mode
		sleep 10
	fi
	mode=$(current_mode)
	log_event "RESTORE mode=$mode"
	[ "$mode" = developer_mode ] || failures=$((failures + 1))
}

cleanup()
{
	restore_developer
	request_result=PASS
	[ "$failures" -eq 0 ] || request_result=FAIL
	log_event "RESULT=$request_result failures=$failures"
}
trap cleanup EXIT HUP INT TERM

mkdir -p "${log%/*}"
log_event "BEGIN dwell=${dwell}s"
snapshot

for mode in tethering_mode mtp_ffs_mode charging_only; do
	log_event "MODE_BEGIN mode=$mode"
	request_mode "$mode" || failures=$((failures + 1))
	sleep "$dwell"
	actual=$(current_mode)
	log_event "MODE_ACTIVE requested=$mode actual=$actual"
	[ "$actual" = "$mode" ] || failures=$((failures + 1))
	restore_developer
	log_event "MODE_END mode=$mode"
	sleep 10
done

exit 0
