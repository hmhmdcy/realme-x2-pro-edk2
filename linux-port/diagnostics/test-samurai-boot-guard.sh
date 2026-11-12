#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
#
# Offline test for samurai-boot-guard's timeout rollback.  It uses ordinary
# temporary files as the two targets, waits for the minimum 60 second arm
# window, and verifies both the image content and the logdump-before-boot
# write order.  It never touches a real block device or reboots the host.

set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
guard=${SAMURAI_BOOT_GUARD_BIN:-$here/samurai-boot-guard.sh}

tmp=$(mktemp -d)
state_dir=$tmp/state
run_dir=$tmp/run
log_file=$tmp/boot-guard.log
boot_image=$state_dir/boot-rollback.img
logdump_image=$state_dir/logdump-rollback.img
boot_target=$tmp/boot-target.img
logdump_target=$tmp/logdump-target.img

cleanup()
{
	if [ -n "${monitor_pid:-}" ]; then
		kill "$monitor_pid" 2>/dev/null || true
		wait "$monitor_pid" 2>/dev/null || true
	fi
	rm -rf "$tmp"
}
trap cleanup EXIT HUP INT TERM

mkdir -p "$state_dir" "$run_dir"
dd if=/dev/zero of="$boot_image" bs=4096 count=1 2>/dev/null
dd if=/dev/zero of="$logdump_image" bs=4096 count=1 2>/dev/null
printf 'rollback-boot-payload\n' |
	dd of="$boot_image" bs=4096 conv=notrunc 2>/dev/null
printf 'rollback-logdump-payload\n' |
	dd of="$logdump_image" bs=4096 conv=notrunc 2>/dev/null
dd if=/dev/zero of="$boot_target" bs=4096 count=1 2>/dev/null
dd if=/dev/zero of="$logdump_target" bs=4096 count=1 2>/dev/null

export SAMURAI_BOOT_GUARD_STATE_DIR=$state_dir
export SAMURAI_BOOT_GUARD_RUN_DIR=$run_dir
export SAMURAI_BOOT_GUARD_LOG=$log_file
export SAMURAI_BOOT_GUARD_BOOT_DEVICE=$boot_target
export SAMURAI_BOOT_GUARD_LOGDUMP_DEVICE=$logdump_target
export SAMURAI_BOOT_GUARD_REBOOT_CMD=true
export SAMURAI_BOOT_GUARD_WAIT_SECONDS=60
export SAMURAI_BOOT_GUARD_INTERVAL=1

"$guard" arm
"$guard" monitor &
monitor_pid=$!

elapsed=0
while [ "$elapsed" -lt 70 ]; do
	if ! kill -0 "$monitor_pid" 2>/dev/null; then
		break
	fi
	sleep 1
	elapsed=$((elapsed + 1))
done

wait "$monitor_pid"
monitor_pid=

cmp -s "$boot_target" "$boot_image" || {
	echo "FAIL: boot target was not restored" >&2
	exit 1
}
cmp -s "$logdump_target" "$logdump_image" || {
	echo "FAIL: logdump target was not restored" >&2
	exit 1
}

order=$(grep 'ROLLBACK_WRITE_BEGIN' "$log_file" |
	sed -n 's/.*name=\([^ ]*\).*/\1/p' |
	tr '\n' ' ')
[ "$order" = "logdump boot " ] || {
	echo "FAIL: rollback order was '$order', expected 'logdump boot '" >&2
	exit 1
}

grep -q 'ROLLBACK_WRITE_OK name=logdump' "$log_file"
grep -q 'ROLLBACK_WRITE_OK name=boot' "$log_file"
grep -q 'ROLLBACK_COMPLETE' "$log_file"

echo "RESULT: boot guard timeout rollback and write order passed"
