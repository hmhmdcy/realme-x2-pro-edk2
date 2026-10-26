#!/bin/sh
# Fixed session82 observations. No configuration data writes or MAC requests.
set -eu
case "${1:-}" in before|after) phase=$1;; *) exit 2;; esac
prefix=/tmp/k82-$phase
[ "$(cat /proc/sys/kernel/random/boot_id)" = 87753933-4992-45d2-aaf5-d9db9c11d1a3 ]
[ ! -e "$prefix-state.txt" ]
[ "$(readlink -f /sys/bus/i2c/devices/i2c-0/of_node)" = /sys/firmware/devicetree/base/soc@0/geniqup@8c0000/i2c@884000 ]
[ "$(readlink -f /sys/bus/i2c/devices/i2c-2/of_node)" = /sys/firmware/devicetree/base/soc@0/geniqup@cc0000/i2c@c94000 ]
[ "$(sha256sum /tmp/read-mp2650 | cut -d ' ' -f1)" = 6ef5467f5a445d718bd783ed86aabe5e93d08c442f483978355ad42ec79d5673 ]
[ "$(sha256sum /tmp/k82-read-stock-temperatures | cut -d ' ' -f1)" = 8792cae1f6d217bd99b5f7940b7eabb14cda35f2cdd49d59b107e5734d6764b1 ]
{
    cat /proc/sys/kernel/random/boot_id
    uname -a
    cat /proc/uptime
    cat /proc/sys/kernel/tainted
    cat /sys/class/power_supply/bq28z610-0/uevent
    cat /sys/module/bq27xxx_battery/parameters/poll_interval
    cat /sys/kernel/debug/dri/1/encoder-0/status
    cat /proc/mounts
} > "$prefix-state.txt" 2>&1
{ cat /proc/uptime; /tmp/read-mp2650 /dev/i2c-0; } > "$prefix-registers.txt" 2>&1
{ cat /proc/uptime; /tmp/k82-read-stock-temperatures /dev/i2c-2; } > "$prefix-temperatures.txt" 2>&1
dmesg > "$prefix-dmesg.txt"
sha256sum "$prefix-state.txt" "$prefix-registers.txt" "$prefix-temperatures.txt" "$prefix-dmesg.txt" > "$prefix-hashes.txt"
tar -cf "$prefix.tar" "$prefix-state.txt" "$prefix-registers.txt" "$prefix-temperatures.txt" "$prefix-dmesg.txt" "$prefix-hashes.txt"
cat "$prefix-state.txt"
cat "$prefix-hashes.txt"
