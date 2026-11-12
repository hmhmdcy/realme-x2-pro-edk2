#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
#
# Exercise the standard postmarketOS usb-moded host_mode API against the
# dual-role kernel.  This is a synthetic role test: it proves the userspace
# mode/URS path and xHCI bring-up, not physical OTG device enumeration.

set -u

log=/var/log/samurai/usb-moded-host-mode.log
role_dir=
cleanup_done=0
failures=0

log_event()
{
	mkdir -p "${log%/*}"
	printf '%s %s\n' "$(date -Is)" "$*" >>"$log"
}

fail()
{
	log_event "FAIL $*"
	failures=$((failures + 1))
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

set_mode()
{
	dbus-send --system --type=method_call --reply-timeout=8000 --print-reply \
		--dest=com.meego.usb_moded /com/meego/usb_moded \
		com.meego.usb_moded.set_mode "string:$1" >/dev/null 2>&1
}

request_mode()
{
	dbus-send --system --type=method_call --reply-timeout=5000 --print-reply \
		--dest=com.meego.usb_moded /com/meego/usb_moded \
		com.meego.usb_moded.mode_request 2>/dev/null |
		sed -n 's/.*string "\(.*\)"/\1/p' | tail -n 1
}

wait_mode()
{
	wanted=$1
	limit=$2
	count=0
	while [ "$count" -lt "$limit" ]; do
		[ "$(request_mode)" = "$wanted" ] && return 0
		count=$((count + 1))
		sleep 1
	done
	return 1
}

snapshot()
{
	label=$1
	role=$(cat "$role_dir/role" 2>/dev/null || echo missing)
	udc=$(cat /sys/class/udc/a600000.usb/state 2>/dev/null || echo missing)
	carrier=$(cat /sys/class/net/usb0/carrier 2>/dev/null || echo missing)
	mode=$(request_mode)
	hosts=$(find /sys/bus/usb/devices -maxdepth 1 -name 'usb[0-9]*' 2>/dev/null |
		tr '\n' ' ')
	log_event "STATE label=$label role=$role udc=$udc carrier=$carrier mode=${mode:-missing} hosts=${hosts:-none}"
}

restore_developer()
{
	set_mode developer_mode || true
	if ! wait_mode developer_mode 20; then
		fail "developer mode did not return"
	fi
	udc=
	carrier=
	count=0
	while [ "$count" -lt 30 ]; do
		udc=$(cat /sys/class/udc/a600000.usb/state 2>/dev/null || echo missing)
		carrier=$(cat /sys/class/net/usb0/carrier 2>/dev/null || echo missing)
		[ "$udc" = configured ] && [ "$carrier" = 1 ] && break
		count=$((count + 1))
		sleep 1
	done
	snapshot restored
	[ "$udc" = configured ] || fail "UDC is $udc after restore"
	[ "$carrier" = 1 ] || fail "usb0 carrier is $carrier after restore"
}

cleanup()
{
	[ "$cleanup_done" -eq 0 ] || return 0
	cleanup_done=1
	restore_developer
	request_result=PASS
	[ "$failures" -eq 0 ] || request_result=FAIL
	log_event "RESULT=$request_result failures=$failures"
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

set_mode host_mode || fail "set_mode host_mode request failed"
wait_mode host_mode 20 || fail "usb-moded did not report host_mode"
snapshot host
[ "$(cat "$role_dir/role")" = host ] || fail "usb_role did not switch to host"

baseline=/root/samurai-tests/check-usb-otg-baseline.sh
if [ -x "$baseline" ]; then
	"$baseline" host >>"$log" 2>&1 || fail "host baseline failed"
else
	fail "host baseline script is missing"
fi

exit 0
