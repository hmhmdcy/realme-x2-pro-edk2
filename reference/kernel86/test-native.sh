#!/bin/sh
# Software client creation/removal only; the mp2650 driver performs fixed reads.
set -eu
prefix=/tmp/k86-native
trace=/sys/kernel/tracing/instances/display
[ ! -e "$prefix.tar.gz" ]
uname -a | grep -q '#86 SMP PREEMPT'
[ "$(cat /proc/sys/kernel/random/boot_id)" != f02d218a-cc7d-4b92-8858-c8eeaeab5777 ]
[ "$(cat /proc/sys/kernel/tainted)" = 0 ]
[ "$(readlink -f /sys/bus/i2c/devices/i2c-0/of_node)" = /sys/firmware/devicetree/base/soc@0/geniqup@8c0000/i2c@884000 ]
[ ! -e /sys/bus/i2c/devices/0-005c ]
[ -d /sys/bus/i2c/drivers/mp2650 ]
[ "$(sha256sum /tmp/k86-read-mp2650 | cut -d ' ' -f1)" = 6ef5467f5a445d718bd783ed86aabe5e93d08c442f483978355ad42ec79d5673 ]
[ "$(sha256sum /tmp/k86-read-mp2650-input | cut -d ' ' -f1)" = ed25b9f497ec10294976f61b4fb67994f3884a42a1d7bc3778e0045f7a9ef3a7 ]
/tmp/k86-read-mp2650 /dev/i2c-0 >"$prefix-before-registers.txt"
cat /sys/class/power_supply/bq28z610-0/uevent >"$prefix-before-battery.txt"
echo 'mp2650 0x5c' >/sys/bus/i2c/devices/i2c-0/new_device
[ "$(readlink -f /sys/bus/i2c/devices/0-005c/driver)" = /sys/bus/i2c/drivers/mp2650 ]
cat /sys/class/power_supply/mp2650-input/uevent >"$prefix-sample1.txt"
ls -l /sys/class/power_supply/mp2650-input/online /sys/class/power_supply/mp2650-input/status /sys/class/power_supply/mp2650-input/voltage_now /sys/class/power_supply/mp2650-input/current_now >"$prefix-permissions.txt"
set +e
/tmp/k86-read-mp2650-input /dev/i2c-0 >"$prefix-busy-refusal.txt" 2>&1
refusal=$?
set -e
echo "reader_exit=$refusal" >>"$prefix-busy-refusal.txt"
[ "$refusal" != 0 ]
sleep 5
cat /sys/class/power_supply/mp2650-input/uevent >"$prefix-sample2.txt"
# Release address ownership to compare the fixed configuration registers.
echo '0x5c' >/sys/bus/i2c/devices/i2c-0/delete_device
[ ! -e /sys/bus/i2c/devices/0-005c ]
/tmp/k86-read-mp2650 /dev/i2c-0 >"$prefix-after-registers.txt"
cmp "$prefix-before-registers.txt" "$prefix-after-registers.txt"
echo 'mp2650 0x5c' >/sys/bus/i2c/devices/i2c-0/new_device
[ "$(readlink -f /sys/bus/i2c/devices/0-005c/driver)" = /sys/bus/i2c/drivers/mp2650 ]
cat /sys/class/power_supply/mp2650-input/uevent >"$prefix-final-input.txt"
{
    cat /proc/sys/kernel/random/boot_id
    uname -a
    cat /proc/uptime
    cat /proc/sys/kernel/tainted
    cat /sys/class/power_supply/bq28z610-0/uevent
    cat /sys/kernel/debug/dri/1/encoder-0/status
    cat "$trace/tracing_on"
    cat "$trace/events/dpu/dpu_enc_frame_done_timeout/trigger"
    ls /sys/bus/i2c/devices
    readlink -f /sys/bus/i2c/devices/0-005c/driver
} >"$prefix-state.txt"
cat /sys/kernel/debug/dri/1/state >"$prefix-drm-state.txt"
cat /sys/kernel/debug/dri/1/kms >"$prefix-kms.txt"
cat /sys/kernel/debug/clk/clk_summary >"$prefix-clocks.txt"
{
    head -c 6682624 /dev/sde11 | sha256sum
    sha256sum /dev/sde32
} >"$prefix-partition-hashes.txt"
dmesg >"$prefix-dmesg.txt"
sha256sum "$prefix"-*.txt >"$prefix-hashes.txt"
tar -cf "$prefix.tar" "$prefix"-*.txt
gzip -c "$prefix.tar" >"$prefix.tar.gz"
cat "$prefix-sample1.txt" "$prefix-sample2.txt" "$prefix-final-input.txt" "$prefix-busy-refusal.txt"
cat "$prefix-state.txt"
sha256sum "$prefix.tar.gz"
