#!/bin/sh
set -eu
mountpoint -q /sys/kernel/debug || mount -t debugfs debugfs /sys/kernel/debug
out=/tmp/k73-display-tests.txt
{
    uname -a
    cat /proc/sys/kernel/random/boot_id
    /tmp/kms-smoke /dev/dri/card1 0
    /tmp/kms-smoke /dev/dri/card1 1
    /tmp/kms-smoke /dev/dri/card1 0
    for brightness in 120 256 400; do
        echo "$brightness" > /sys/class/backlight/ae94000.dsi.0/brightness
        cat /sys/class/backlight/ae94000.dsi.0/brightness
    done
    cat /sys/class/drm/card1-DSI-1/status
    cat /proc/sys/kernel/tainted
} > "$out" 2>&1
sha256sum "$out"
cat "$out"
