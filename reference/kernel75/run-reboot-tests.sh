#!/bin/sh
set -eu
mountpoint -q /sys/kernel/debug || mount -t debugfs debugfs /sys/kernel/debug
chmod 755 /tmp/kms-smoke
export VK_DRIVER_FILES=/tmp/k75-gpu/freedreno.json
export LD_LIBRARY_PATH=/tmp/k75-gpu/lib
{
    uname -a
    cat /proc/sys/kernel/random/boot_id
    /tmp/k75-gpu/lib/ld-linux-aarch64.so.1 /tmp/k75-gpu/gpu-render 12
    /tmp/kms-smoke /dev/dri/card1 0
    /tmp/kms-smoke /dev/dri/card1 1
    /tmp/kms-smoke /dev/dri/card1 0
    echo TAINT
    cat /proc/sys/kernel/tainted
    test "$(cat /proc/sys/kernel/tainted)" = 0
} >/tmp/k75-reboot-tests.txt 2>&1
gzip -c /tmp/k75-reboot-tests.txt >/tmp/k75-reboot-tests.gz
dmesg >/tmp/k75-reboot-complete-dmesg.txt
gzip -c /tmp/k75-reboot-complete-dmesg.txt >/tmp/k75-reboot-complete-dmesg.gz
sha256sum /tmp/k75-reboot-tests.txt /tmp/k75-reboot-tests.gz /tmp/k75-reboot-complete-dmesg.txt /tmp/k75-reboot-complete-dmesg.gz
cat /tmp/k75-reboot-tests.txt
