#!/bin/sh
# Session81 final fixed observations: no flash/reboot/panel cycle/settings.
set -eu
[ "$(cat /proc/sys/kernel/random/boot_id)" = 87753933-4992-45d2-aaf5-d9db9c11d1a3 ]
[ ! -e /tmp/k81-final-state.txt ]
[ "$(readlink -f /sys/bus/i2c/devices/i2c-0/of_node)" = /sys/firmware/devicetree/base/soc@0/geniqup@8c0000/i2c@884000 ]
[ "$(readlink -f /sys/bus/i2c/devices/i2c-2/of_node)" = /sys/firmware/devicetree/base/soc@0/geniqup@cc0000/i2c@c94000 ]
[ "$(sha256sum /tmp/read-mp2650 | cut -d ' ' -f1)" = 6ef5467f5a445d718bd783ed86aabe5e93d08c442f483978355ad42ec79d5673 ]
{ cat /proc/uptime; /tmp/read-mp2650 /dev/i2c-0; } > /tmp/k81-final-registers.txt 2>&1
{
    cat /proc/sys/kernel/random/boot_id
    uname -a
    cat /proc/uptime
    cat /proc/sys/kernel/tainted
    cat /sys/class/power_supply/bq28z610-0/uevent
    cat /sys/kernel/debug/dri/1/kms
    cat /sys/kernel/debug/dri/1/state
    cat /sys/kernel/debug/dri/1/encoder-0/status
    cat /proc/mounts
} > /tmp/k81-final-state.txt 2>&1
dmesg > /tmp/k81-final-dmesg.txt
gzip -c /tmp/k81-final-dmesg.txt > /tmp/k81-final-dmesg.txt.gz
sha256sum /tmp/k81-stock-state.txt /tmp/k81-before-dmesg.txt /tmp/k81-after-dmesg.txt \
    /tmp/k81-stock-temperatures.txt /tmp/k81-firmware-inventory.txt /tmp/k81-wifi-extraction.txt \
    /tmp/k81-wifi-firmware-stock.tar /tmp/k81-final-registers.txt /tmp/k81-final-state.txt \
    /tmp/k81-final-dmesg.txt /tmp/k81-final-dmesg.txt.gz > /tmp/k81-device-hashes.txt
cat /tmp/k81-final-registers.txt
cat /tmp/k81-device-hashes.txt
