#!/bin/sh
# Exercise the distro usb-signaller stack without making it persistent.
#
# This is a board bring-up test: it stops the legacy samurai-usb owner and
# the bounded recovery service, asks usb-signaller for a mode, records the
# resulting standard configfs/UDC/NetworkManager state, and restores the
# standard usb-signaller developer mode unless KEEP=1.
set -eu

MODE=${MODE:-developer_mode}
WAIT=${WAIT:-30}
LOG=${LOG:-/tmp/usb-signaller-bringup.log}
KEEP=${KEEP:-0}
KEEP_ON_FAIL=${KEEP_ON_FAIL:-0}
QMULT=${QMULT:-20}
NUDGE=${NUDGE:-1}
DBUS_DEST=com.meego.usb_moded
DBUS_PATH=/com/meego/usb_moded
DBUS_IFACE=com.meego.usb_moded
CONFIGFS=/sys/kernel/config/usb_gadget
UDC_DIR=${SAMURAI_UDC_DIR:-/sys/class/udc}

exec >>"$LOG" 2>&1

log()
{
	printf '%s %s\n' "$(date -Is)" "$*"
}

dbus_call()
{
	dbus-send --system --type=method_call --print-reply \
		--dest="$DBUS_DEST" "$DBUS_PATH" "$DBUS_IFACE.$1" ${2-} 2>/dev/null
}

dbus_string()
{
	dbus_call "$1" | sed -n 's/.*string "\(.*\)"/\1/p' | tail -n 1
}

current_mode()
{
	dbus_string mode_request
}

available_modes()
{
	dbus_string get_modes
}

snapshot()
{
	label=$1
	printf '\n=== %s ===\n' "$label"
	printf 'boot_id=%s\n' "$(cat /proc/sys/kernel/random/boot_id)"
	printf 'mode=%s\n' "$(current_mode || true)"
	printf 'modes=%s\n' "$(available_modes || true)"
	for udc in "$UDC_DIR"/*; do
		[ -e "$udc" ] || continue
		printf 'udc.%s.state=%s\n' "${udc##*/}" "$(cat "$udc/state" 2>/dev/null || true)"
	done
	for gadget in "$CONFIGFS"/*; do
		[ -d "$gadget" ] || continue
		printf 'gadget.%s.udc=%s\n' "${gadget##*/}" "$(cat "$gadget/UDC" 2>/dev/null || true)"
	done
	for path in "$CONFIGFS"/*/functions/ncm.*/qmult; do
		[ -e "$path" ] && printf 'qmult.%s=%s\n' "$path" "$(cat "$path" 2>/dev/null || true)"
	done
	ip -br addr show usb0 2>/dev/null || true
	nmcli -t -f NAME,TYPE,DEVICE,STATE connection show 2>/dev/null |
		grep -E 'Developer Mode|Tethering Mode|usb0' || true
}

stop_legacy()
{
	rc-service samurai-usb-recover stop >/dev/null 2>&1 || true
	rc-service samurai-usb stop >/dev/null 2>&1 || true
	rc-service usb-signaller stop >/dev/null 2>&1 || true
	# usb-signaller's gadget parser requires a configuration description
	# before it can take ownership of an already-created gadget.  The
	# legacy samurai-usb gadget predates that requirement; add the standard
	# configfs string so the migration path does not panic in usb-signaller.
	if [ -d "$CONFIGFS/samurai/configs/c.1" ] &&
		[ ! -e "$CONFIGFS/samurai/configs/c.1/strings/0x409/configuration" ]; then
		mkdir -p "$CONFIGFS/samurai/configs/c.1/strings/0x409"
		printf 'Samurai NCM\n' \
			>"$CONFIGFS/samurai/configs/c.1/strings/0x409/configuration" ||
			true
	fi
}

restore_standard()
{
	log 'restoring usb-signaller developer mode'
	rc-service samurai-usb-recover stop >/dev/null 2>&1 || true
	rc-service samurai-usb stop >/dev/null 2>&1 || true
	rc-service usb-signaller start >/dev/null 2>&1 || true
	count=0
	while [ "$count" -lt 30 ]; do
		if available_modes | grep -q charging_only; then
			break
		fi
		count=$((count + 1))
		sleep 1
	done
	dbus_call set_mode "string:developer_mode" >/dev/null 2>&1 || true
	rc-service usb-signaller-developer-mode restart >/dev/null 2>&1 || true
	rc-service samurai-usb-recover start >/dev/null 2>&1 || true
}

nudge_udc()
{
	for udc in "$UDC_DIR"/*; do
		[ -e "$udc" ] || continue
		[ -w "$udc/soft_connect" ] || continue
		log "nudging UDC ${udc##*/} through soft_connect"
		printf 'disconnect\n' >"$udc/soft_connect" 2>/dev/null || true
		sleep 1
		printf 'connect\n' >"$udc/soft_connect" 2>/dev/null || true
	done
}

cleanup()
{
	rc=$?
	trap - EXIT INT TERM
	if { [ "$rc" -ne 0 ] && [ "$KEEP_ON_FAIL" != 1 ]; } ||
		{ [ "$rc" -eq 0 ] && [ "$KEEP" != 1 ]; }; then
		restore_standard
	fi
	printf '\n=== RESULT rc=%s mode=%s keep=%s keep_on_fail=%s ===\n' \
		"$rc" "$MODE" "$KEEP" "$KEEP_ON_FAIL"
	exit "$rc"
}

trap cleanup EXIT INT TERM

log "starting mode=$MODE wait=$WAIT qmult=$QMULT"
snapshot before

stop_legacy
log 'starting usb-signaller'
rc-service usb-signaller start

count=0
while [ "$count" -lt "$WAIT" ]; do
	if available_modes | grep -q charging_only; then
		break
	fi
	count=$((count + 1))
	sleep 1
done
[ "$count" -lt "$WAIT" ] || {
	log 'usb-signaller D-Bus did not become ready'
	exit 1
}

if [ "$(current_mode)" != "$MODE" ]; then
	log "requesting mode=$MODE"
	dbus_call set_mode "string:$MODE" >/dev/null
fi

count=0
while [ "$count" -lt "$WAIT" ]; do
	mode=$(current_mode || true)
	[ "$mode" = "$MODE" ] && break
	count=$((count + 1))
	sleep 1
done
[ "$count" -lt "$WAIT" ] || {
	log "mode did not become $MODE (current=$mode)"
	exit 1
}

if [ "$MODE" = developer_mode ] || [ "$MODE" = tethering_mode ]; then
	count=0
	while [ "$count" -lt "$WAIT" ]; do
		configured=0
		for udc in "$UDC_DIR"/*; do
			[ -e "$udc" ] || continue
			[ "$(cat "$udc/state" 2>/dev/null || true)" = configured ] &&
				configured=1
		done
		[ "$configured" = 1 ] && break
		if [ "$NUDGE" = 1 ] && [ "$count" -eq 5 ]; then
			nudge_udc
		fi
		count=$((count + 1))
		sleep 1
	done
	[ "$count" -lt "$WAIT" ] || {
		log "UDC did not become configured for $MODE"
		exit 1
	}
	if [ "$MODE" = developer_mode ] || [ "$MODE" = tethering_mode ]; then
		found_qmult=0
		for path in "$CONFIGFS"/*/functions/ncm.*/qmult; do
			[ -e "$path" ] || continue
			found_qmult=1
			actual=$(cat "$path" 2>/dev/null || true)
			log "qmult $path=$actual"
			[ "$actual" = "$QMULT" ] || {
				log "unexpected qmult: expected $QMULT, got $actual"
				exit 1
			}
		done
		[ "$found_qmult" -eq 1 ] || {
			log 'no NCM qmult control found'
			exit 1
		}
	fi
elif [ "$MODE" = mtp_ffs_mode ]; then
	count=0
	while [ "$count" -lt "$WAIT" ]; do
		[ -e /dev/mtp/ep0 ] && break
		count=$((count + 1))
		sleep 1
	done
	[ "$count" -lt "$WAIT" ] || {
		log 'MTP FunctionFS endpoints did not appear'
		exit 1
	}
fi

sleep 2
snapshot after
log "mode=$MODE passed"
