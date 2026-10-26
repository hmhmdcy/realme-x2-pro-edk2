#!/bin/sh
set -eu
mountpoint -q /sys/kernel/debug || mount -t debugfs debugfs /sys/kernel/debug
chmod 755 /tmp/read-gauge /tmp/kms-smoke
out=/tmp/k77-gauge-tests.txt
{
    uname -a
    cat /proc/sys/kernel/random/boot_id
    echo DSI_BEFORE
    dmesg | grep -c dsi_err_worker || true
    /tmp/kms-smoke /dev/dri/card1 0
    echo GPU_REGRESSION
    VK_DRIVER_FILES=/tmp/k75-gpu/freedreno.json LD_LIBRARY_PATH=/tmp/k75-gpu/lib /tmp/k75-gpu/lib/ld-linux-aarch64.so.1 /tmp/k75-gpu/gpu-render 12
    echo DSI_AFTER_PANEL_CYCLE
    dmesg | grep -c dsi_err_worker || true
    for sample in $(seq 1 30); do
        echo SAMPLE=$sample
        cat /proc/uptime
        cat /sys/class/power_supply/bq28z610-0/uevent
        /tmp/read-gauge /dev/i2c-1
        sleep 2
    done
    echo DSI_AFTER_SAMPLING
    dmesg | grep -c dsi_err_worker || true
    echo TAINT
    cat /proc/sys/kernel/tainted
    test "$(cat /proc/sys/kernel/tainted)" = 0
} > "$out" 2>&1
gzip -c "$out" > "$out.gz"
dmesg > /tmp/k77-complete-dmesg.txt
gzip -c /tmp/k77-complete-dmesg.txt > /tmp/k77-complete-dmesg.gz
sha256sum "$out" "$out.gz" /tmp/k77-complete-dmesg.txt /tmp/k77-complete-dmesg.gz
tail -20 "$out"
