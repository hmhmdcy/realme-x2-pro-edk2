#!/bin/sh
#
# Put the Samurai NCM device on a Linux host into USB autosuspend.  This is
# the standard host-side interface needed to make the DWC3 link enter U3 so
# the qcom DP/DM PDC wake IRQs can be exercised.
#
# Run as root on the Linux host, with the phone connected by USB:
#   sh linux-host-usb-autosuspend.sh
#
set -eu

found=0
for dev in /sys/bus/usb/devices/*; do
	[ -r "$dev/idVendor" ] || continue
	[ -r "$dev/idProduct" ] || continue
	if [ "$(cat "$dev/idVendor")" != "0525" ] ||
	   [ "$(cat "$dev/idProduct")" != "a4a1" ]; then
		continue
	fi

	if [ ! -w "$dev/power/control" ]; then
		echo "not writable: $dev/power/control" >&2
		exit 1
	fi

	echo auto > "$dev/power/control"
	if [ -w "$dev/power/autosuspend_delay_ms" ]; then
		echo 1000 > "$dev/power/autosuspend_delay_ms"
	fi

	echo "configured $dev"
	echo "control=$(cat "$dev/power/control")"
	echo "delay_ms=$(cat "$dev/power/autosuspend_delay_ms" 2>/dev/null || echo n/a)"
	echo "state=$(cat "$dev/power/runtime_status" 2>/dev/null || echo n/a)"
	found=1
done

if [ "$found" -eq 0 ]; then
	echo "Samurai NCM device 0525:a4a1 not found" >&2
	exit 2
fi
