#!/bin/sh
set -eu
prefix=/tmp/k85-chemistry
trace=/sys/kernel/tracing/instances/display
[ ! -e "$prefix.tar" ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = f02d218a-cc7d-4b92-8858-c8eeaeab5777 ]
uname -a | grep -q '#85 SMP PREEMPT'
[ "$(sha256sum /tmp/k85-read-stock-chemistry | cut -d ' ' -f1)" = f78d968f93752142ea839a61de3323139b89139f1ac3c463cb67499d78744bc9 ]
[ "$(sha256sum /tmp/k85-read-stock-temperatures | cut -d ' ' -f1)" = 8792cae1f6d217bd99b5f7940b7eabb14cda35f2cdd49d59b107e5734d6764b1 ]
[ "$(sha256sum /tmp/k84-read-mp2650 | cut -d ' ' -f1)" = 6ef5467f5a445d718bd783ed86aabe5e93d08c442f483978355ad42ec79d5673 ]
{
    cat /proc/uptime
    cat /proc/sys/kernel/tainted
    cat /sys/class/power_supply/bq28z610-0/uevent
    cat /sys/kernel/debug/dri/1/encoder-0/status
    cat "$trace/tracing_on"
    cat "$trace/events/dpu/dpu_enc_frame_done_timeout/trigger"
} >"$prefix-before-state.txt"
dmesg >"$prefix-before-dmesg.txt"
grep -q 'frame_done_cnt:0mode:' "$prefix-before-state.txt"
/tmp/k85-read-stock-temperatures /dev/i2c-2 >"$prefix-before-temperatures.txt"
set +e
/tmp/k85-read-stock-chemistry /dev/i2c-2 >"$prefix-query.txt" 2>&1
reader_code=$?
set -e
echo "$reader_code" >"$prefix-reader-exit.txt"
/tmp/k85-read-stock-temperatures /dev/i2c-2 >"$prefix-after-temperatures.txt"
/tmp/k84-read-mp2650 /dev/i2c-0 >"$prefix-mp2650.txt"
{
    cat /proc/uptime
    cat /proc/sys/kernel/tainted
    cat /sys/class/power_supply/bq28z610-0/uevent
    cat /sys/kernel/debug/dri/1/encoder-0/status
    cat "$trace/tracing_on"
    cat "$trace/events/dpu/dpu_enc_frame_done_timeout/trigger"
} >"$prefix-after-state.txt"
dmesg >"$prefix-after-dmesg.txt"
sha256sum "$prefix-before-state.txt" "$prefix-before-dmesg.txt" "$prefix-before-temperatures.txt" "$prefix-query.txt" "$prefix-reader-exit.txt" "$prefix-after-temperatures.txt" "$prefix-mp2650.txt" "$prefix-after-state.txt" "$prefix-after-dmesg.txt" /tmp/k85-chemistry-refusal.txt >"$prefix-hashes.txt"
tar -cf "$prefix.tar" "$prefix-before-state.txt" "$prefix-before-dmesg.txt" "$prefix-before-temperatures.txt" "$prefix-query.txt" "$prefix-reader-exit.txt" "$prefix-after-temperatures.txt" "$prefix-mp2650.txt" "$prefix-after-state.txt" "$prefix-after-dmesg.txt" /tmp/k85-chemistry-refusal.txt "$prefix-hashes.txt"
gzip -c "$prefix.tar" >"$prefix.tar.gz"
cat "$prefix-query.txt"
echo "reader_exit=$reader_code"
cat "$prefix-after-temperatures.txt"
sha256sum "$prefix.tar" "$prefix.tar.gz"
exit "$reader_code"
