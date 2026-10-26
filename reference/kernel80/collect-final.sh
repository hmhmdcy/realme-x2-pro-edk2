#!/bin/sh
# Session80 bounded observations, on the already-verified session79 boot.
# No flash, reboot, panel cycle, charging settings, NVM or USB role changes.
set -eu
test "$(cat /proc/sys/kernel/random/boot_id)" = 87753933-4992-45d2-aaf5-d9db9c11d1a3
test ! -e /tmp/k80-final-state.txt
test "$(readlink -f /sys/bus/i2c/devices/i2c-0/of_node)" = /sys/firmware/devicetree/base/soc@0/geniqup@8c0000/i2c@884000
test "$(readlink -f /sys/bus/i2c/devices/i2c-2/of_node)" = /sys/firmware/devicetree/base/soc@0/geniqup@cc0000/i2c@c94000
test "$(sha256sum /tmp/read-mp2650 | cut -d ' ' -f1)" = 6ef5467f5a445d718bd783ed86aabe5e93d08c442f483978355ad42ec79d5673
{
    cat /proc/uptime
    /tmp/read-mp2650 /dev/i2c-0
    /tmp/read-gauge /dev/i2c-2
} > /tmp/k80-final-registers.txt 2>&1
{
    cat /proc/sys/kernel/random/boot_id
    uname -a
    cat /proc/uptime
    cat /proc/sys/kernel/tainted
    cat /sys/class/power_supply/bq28z610-0/uevent
    cat /sys/kernel/debug/dri/1/kms
    cat /sys/kernel/debug/dri/1/state
    cat /sys/kernel/debug/dri/1/encoder-0/status
} > /tmp/k80-final-state.txt 2>&1
dmesg > /tmp/k80-final-dmesg.txt
gzip -c /tmp/k80-final-dmesg.txt > /tmp/k80-final-dmesg.txt.gz
sha256sum /tmp/k80-before-state.txt /tmp/k80-before-dmesg.txt \
    /tmp/k80-identity.txt /tmp/k80-identity-after-dmesg.txt /tmp/k80-legacy.txt \
    /tmp/k80-paired-identity.txt /tmp/k80-firmware-version.txt /tmp/k80-stock-cells.txt \
    /tmp/k80-final-registers.txt /tmp/k80-final-state.txt \
    /tmp/k80-final-dmesg.txt /tmp/k80-final-dmesg.txt.gz > /tmp/k80-device-hashes.txt
cat /tmp/k80-final-registers.txt
cat /tmp/k80-device-hashes.txt
