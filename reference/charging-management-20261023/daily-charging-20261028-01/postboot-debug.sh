#!/bin/sh
set -u

echo "boot_id=$(cat /proc/sys/kernel/random/boot_id)"
echo "uptime=$(cat /proc/uptime)"
echo "driver=$(readlink -f /sys/bus/i2c/devices/0-005c/driver)"
echo "service_state:"
rc-service samurai-charging status 2>&1 || true
echo "service_run_state:"
ls -l /run/openrc/started/samurai-charging \
    /run/openrc/stopped/samurai-charging 2>&1 || true
echo "modules:"
lsmod | grep -E 'samurai|mp2650' || true
echo "failure:"
cat /var/lib/samurai/charging-managed/last-failure-private.txt 2>/dev/null || true
echo "state:"
cat /var/lib/samurai/charging-managed/state-private.json 2>/dev/null || true
echo "dmesg:"
dmesg | grep -E 'samurai[-_]mp2650|samurai-usb-input|samurai-gauge|udevd|charging' | tail -80
echo "service_log:"
cat /var/log/messages 2>/dev/null | grep -i samurai-charging | tail -50 || true
