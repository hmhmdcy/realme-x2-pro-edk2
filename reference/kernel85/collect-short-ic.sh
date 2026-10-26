#!/bin/sh
# Fixed observations only. Preserve any display failure instead of recovering it.
set -eu
prefix=/tmp/k85-short
trace=/sys/kernel/tracing/instances/display
[ ! -e "$prefix.tar" ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = f02d218a-cc7d-4b92-8858-c8eeaeab5777 ]
uname -a | grep -q '#85 SMP PREEMPT'
[ "$(readlink -f /sys/bus/i2c/devices/i2c-2/of_node)" = /sys/firmware/devicetree/base/soc@0/geniqup@cc0000/i2c@c94000 ]
[ "$(sha256sum /tmp/k85-read-short-ic | cut -d ' ' -f1)" = e4d7b535564ab01a8f4ddebf97961adf2faac63b19e29ebcaaf7a7716c792553 ]
[ "$(sha256sum /tmp/k84-read-mp2650 | cut -d ' ' -f1)" = 6ef5467f5a445d718bd783ed86aabe5e93d08c442f483978355ad42ec79d5673 ]
{
    cat /proc/sys/kernel/random/boot_id
    uname -a
    cat /proc/uptime
    cat /proc/sys/kernel/tainted
    cat /sys/class/power_supply/bq28z610-0/uevent
    cat /sys/kernel/debug/dri/1/encoder-0/status
    cat "$trace/tracing_on"
    cat "$trace/events/dpu/dpu_enc_frame_done_timeout/trigger"
} >"$prefix-before-state.txt"
dmesg >"$prefix-before-dmesg.txt"
grep -q 'frame_done_cnt:0mode:' "$prefix-before-state.txt"
/tmp/k84-read-mp2650 /dev/i2c-0 >"$prefix-before-mp2650.txt"
set +e
/tmp/k85-read-short-ic /dev/i2c-2 >"$prefix-registers.txt" 2>&1
reader_code=$?
set -e
echo "$reader_code" >"$prefix-reader-exit.txt"
/tmp/k84-read-mp2650 /dev/i2c-0 >"$prefix-after-mp2650.txt"
{
    cat /proc/uptime
    cat /proc/sys/kernel/tainted
    cat /sys/class/power_supply/bq28z610-0/uevent
    cat /sys/kernel/debug/dri/1/encoder-0/status
    cat "$trace/tracing_on"
    cat "$trace/events/dpu/dpu_enc_frame_done_timeout/trigger"
} >"$prefix-after-state.txt"
grep -qx 'PARTNAME=boot' /sys/class/block/sde11/uevent
grep -qx 'PARTNAME=logdump' /sys/class/block/sde32/uevent
[ "$(cat /sys/class/block/sde11/size)" = 196608 ]
[ "$(cat /sys/class/block/sde32/size)" = 131072 ]
{
    head -c 6682624 /dev/sde11 | sha256sum
    sha256sum /dev/sde32
} >"$prefix-partition-hashes.txt"
dmesg >"$prefix-after-dmesg.txt"
sha256sum "$prefix-before-state.txt" "$prefix-before-dmesg.txt" "$prefix-before-mp2650.txt" "$prefix-registers.txt" "$prefix-reader-exit.txt" "$prefix-after-mp2650.txt" "$prefix-after-state.txt" "$prefix-partition-hashes.txt" "$prefix-after-dmesg.txt" >"$prefix-hashes.txt"
tar -cf "$prefix.tar" "$prefix-before-state.txt" "$prefix-before-dmesg.txt" "$prefix-before-mp2650.txt" "$prefix-registers.txt" "$prefix-reader-exit.txt" "$prefix-after-mp2650.txt" "$prefix-after-state.txt" "$prefix-partition-hashes.txt" "$prefix-after-dmesg.txt" "$prefix-hashes.txt"
gzip -c "$prefix.tar" >"$prefix.tar.gz"
cat "$prefix-registers.txt"
echo "reader_exit=$reader_code"
cat "$prefix-after-state.txt"
sha256sum "$prefix.tar" "$prefix.tar.gz"
exit "$reader_code"
