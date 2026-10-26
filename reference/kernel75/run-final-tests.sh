#!/bin/sh
set -eu
mountpoint -q /sys/kernel/debug || mount -t debugfs debugfs /sys/kernel/debug
chmod 755 /tmp/kms-smoke
export VK_DRIVER_FILES=/tmp/k75-gpu/freedreno.json
export LD_LIBRARY_PATH=/tmp/k75-gpu/lib
out=/tmp/k75-final-tests.txt
{
    uname -a
    cat /proc/sys/kernel/random/boot_id
    echo GPU_FREQUENCIES_BEFORE
    cat /sys/class/devfreq/2c00000.gpu/available_frequencies
    cat /sys/class/devfreq/2c00000.gpu/trans_stat
    for cycle in 1 2 3; do
        echo "mixed_cycle=$cycle"
        /tmp/k75-gpu/lib/ld-linux-aarch64.so.1 /tmp/k75-gpu/gpu-render 3000
        /tmp/kms-smoke /dev/dri/card1 0
        /tmp/kms-smoke /dev/dri/card1 1
        /tmp/kms-smoke /dev/dri/card1 0
        sleep 2
        /tmp/k75-gpu/lib/ld-linux-aarch64.so.1 /tmp/k75-gpu/gpu-render 12
    done
    echo GPU_FREQUENCIES_AFTER
    cat /sys/class/devfreq/2c00000.gpu/trans_stat
    cat /sys/class/devfreq/2c00000.gpu/cur_freq
    cat /sys/class/devfreq/2c00000.gpu/target_freq
    for brightness in 120 256 400; do
        echo "$brightness" > /sys/class/backlight/ae94000.dsi.0/brightness
        cat /sys/class/backlight/ae94000.dsi.0/brightness
    done
    cat /sys/class/drm/card1-DSI-1/status
    echo TAINT
    cat /proc/sys/kernel/tainted
    test "$(cat /proc/sys/kernel/tainted)" = 0
} > "$out" 2>&1
gzip -c "$out" > "$out.gz"
sha256sum "$out" "$out.gz"
cat "$out"
