#!/bin/sh
#
# Read-only post-coldboot gate for the SOFEF03F HBM fix.
# Run after: poweroff -> remove external power -> press physical power key.
# Compare boot_id with the pre-coldboot value and confirm the user visually
# saw the panel light up; this script cannot prove the physical panel state.
#
set -u

DSI=$(ls -d /sys/class/drm/card*-DSI-1 2>/dev/null | head -1)
BL=$(ls -d /sys/class/backlight/* 2>/dev/null | head -1)

echo "uname=$(uname -r)"
echo "boot_id=$(cat /proc/sys/kernel/random/boot_id)"
echo "uptime=$(cut -d. -f1 /proc/uptime)s"
echo "dsi=$(cat "$DSI/dpms" 2>/dev/null),$(cat "$DSI/enabled" 2>/dev/null)"
echo "backlight=$(cat "$BL/brightness" 2>/dev/null),$(cat "$BL/bl_power" 2>/dev/null)"
echo "hbm_errors=$(dmesg | grep -icE "HBM enable failed|HBM disable failed|Brightness write .* failed|post-on display-on failed" || true)"
echo "kwin_atomic_commit_failed=$(grep -c "Atomic commit failed" /home/cy122/.local/state/tinydm.log 2>/dev/null || true)"
echo "hbm_log:"
dmesg | grep -iE "post-on display-on completed|brightness wrote|HBM" | tail -10 || true
echo "network:"
ip -brief addr show 2>/dev/null | grep -E "usb0|wlan0" || true
for udc in /sys/class/udc/*; do
	[ -e "$udc/state" ] || continue
	echo "udc=$(basename "$udc"),state=$(cat "$udc/state")"
done
