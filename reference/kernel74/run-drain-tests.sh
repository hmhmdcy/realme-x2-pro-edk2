#!/bin/sh
set -eu
mountpoint -q /sys/kernel/debug || mount -t debugfs debugfs /sys/kernel/debug
chmod 755 /tmp/kms-smoke
out=/tmp/k74-drain-display-tests.txt
{
    uname -a
    cat /proc/sys/kernel/random/boot_id
    for cycle in 1 2 3; do
        echo "cycle=$cycle"
        /tmp/kms-smoke /dev/dri/card1 0
        /tmp/kms-smoke /dev/dri/card1 1
        /tmp/kms-smoke /dev/dri/card1 0
    done
    for brightness in 120 256 400; do
        echo "$brightness" > /sys/class/backlight/ae94000.dsi.0/brightness
        cat /sys/class/backlight/ae94000.dsi.0/brightness
    done
    cat /sys/class/drm/card1-DSI-1/status
    cat /proc/sys/kernel/tainted
} > "$out" 2>&1
gzip -c "$out" > "$out.gz"
sha256sum "$out" "$out.gz"
cat "$out"
