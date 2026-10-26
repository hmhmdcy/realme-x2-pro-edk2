#!/bin/sh
# Preserve the old live boot before any diagnostic deployment.
set -eu
prefix=/tmp/k84-before
[ "$(cat /proc/sys/kernel/random/boot_id)" = 87753933-4992-45d2-aaf5-d9db9c11d1a3 ]
[ ! -e "$prefix.tar" ]
grep -qx 'PARTNAME=boot' /sys/class/block/sde11/uevent
grep -qx 'PARTNAME=logdump' /sys/class/block/sde32/uevent
[ "$(cat /sys/class/block/sde11/size)" = 196608 ]
[ "$(cat /sys/class/block/sde32/size)" = 131072 ]
[ "$(readlink -f /sys/bus/i2c/devices/i2c-0/of_node)" = /sys/firmware/devicetree/base/soc@0/geniqup@8c0000/i2c@884000 ]
[ "$(readlink -f /sys/bus/i2c/devices/i2c-2/of_node)" = /sys/firmware/devicetree/base/soc@0/geniqup@cc0000/i2c@c94000 ]
[ "$(sha256sum /tmp/read-mp2650 | cut -d ' ' -f1)" = 6ef5467f5a445d718bd783ed86aabe5e93d08c442f483978355ad42ec79d5673 ]
[ "$(sha256sum /tmp/k82-read-stock-temperatures | cut -d ' ' -f1)" = 8792cae1f6d217bd99b5f7940b7eabb14cda35f2cdd49d59b107e5734d6764b1 ]
{
    cat /proc/sys/kernel/random/boot_id
    uname -a
    cat /proc/uptime
    cat /proc/sys/kernel/tainted
    cat /proc/cmdline
    cat /sys/class/power_supply/bq28z610-0/uevent
    cat /sys/kernel/debug/dri/1/encoder-0/status
    cat /sys/class/block/sde11/uevent
    cat /sys/class/block/sde32/uevent
    cat /sys/class/block/sde11/size
    cat /sys/class/block/sde32/size
} >"$prefix-state.txt" 2>&1
cat /sys/kernel/debug/dri/1/state >"$prefix-drm-state.txt"
cat /sys/kernel/debug/dri/1/kms >"$prefix-kms.txt"
cat /sys/kernel/debug/clk/clk_summary >"$prefix-clocks.txt"
/tmp/read-mp2650 /dev/i2c-0 >"$prefix-registers.txt"
/tmp/k82-read-stock-temperatures /dev/i2c-2 >"$prefix-temperatures.txt"
{
    head -c 6682624 /dev/sde11 | sha256sum
    sha256sum /dev/sde32
} >"$prefix-partition-hashes.txt"
grep -q '^08edf9bcc1c55977169b0a8fd9f963805ba98d0423929e09e17bb9f811ca7405 ' "$prefix-partition-hashes.txt"
grep -q '^607fc6b4b0caba8ca5c7ea6677fd8259c81a216f91b2d6de7603e3f56d9881d0 ' "$prefix-partition-hashes.txt"
dmesg >"$prefix-dmesg.txt"
sha256sum "$prefix-state.txt" "$prefix-drm-state.txt" "$prefix-kms.txt" "$prefix-clocks.txt" "$prefix-registers.txt" "$prefix-temperatures.txt" "$prefix-partition-hashes.txt" "$prefix-dmesg.txt" >"$prefix-hashes.txt"
tar -cf "$prefix.tar" "$prefix-state.txt" "$prefix-drm-state.txt" "$prefix-kms.txt" "$prefix-clocks.txt" "$prefix-registers.txt" "$prefix-temperatures.txt" "$prefix-partition-hashes.txt" "$prefix-dmesg.txt" "$prefix-hashes.txt"
cat "$prefix-state.txt"
cat "$prefix-partition-hashes.txt"
