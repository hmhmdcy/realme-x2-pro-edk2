#!/bin/sh
set -eu
out=/tmp/k77-recheck-samples.txt
{
    uname -a
    cat /proc/sys/kernel/random/boot_id
    echo DSI_BEFORE_SAMPLING
    dmesg | grep -c dsi_err_worker || true
    for sample in $(seq 1 15); do
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
dmesg > /tmp/k77-recheck-complete-dmesg.txt
gzip -c /tmp/k77-recheck-complete-dmesg.txt > /tmp/k77-recheck-complete-dmesg.gz
sha256sum "$out" "$out.gz" /tmp/k77-recheck-complete-dmesg.txt /tmp/k77-recheck-complete-dmesg.gz /tmp/k77-recheck-kms.txt
tail -16 "$out"
