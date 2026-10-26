#!/bin/sh
set -eu
prefix=/tmp/k86-input
trace=/sys/kernel/tracing/instances/display
[ ! -e "$prefix.tar" ]
[ ! -e "$prefix-before-state.txt" ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = f02d218a-cc7d-4b92-8858-c8eeaeab5777 ]
[ "$(sha256sum /tmp/k86-read-mp2650-input | cut -d ' ' -f1)" = ed25b9f497ec10294976f61b4fb67994f3884a42a1d7bc3778e0045f7a9ef3a7 ]
[ "$(sha256sum /tmp/k84-read-mp2650 | cut -d ' ' -f1)" = 6ef5467f5a445d718bd783ed86aabe5e93d08c442f483978355ad42ec79d5673 ]
state() {
    cat /proc/sys/kernel/random/boot_id
    uname -a
    cat /proc/uptime
    cat /proc/sys/kernel/tainted
    cat /sys/class/power_supply/bq28z610-0/uevent
    cat /sys/kernel/debug/dri/1/encoder-0/status
    cat "$trace/tracing_on"
    cat "$trace/events/dpu/dpu_enc_frame_done_timeout/trigger"
}
state >"$prefix-before-state.txt"
dmesg >"$prefix-before-dmesg.txt"
grep -q 'frame_done_cnt:0mode:' "$prefix-before-state.txt"
/tmp/k84-read-mp2650 /dev/i2c-0 >"$prefix-before-registers.txt"
{
    cat /sys/class/udc/a600000.usb/state
    cat /sys/class/udc/a600000.usb/current_speed
    cat /sys/class/udc/a600000.usb/maximum_speed
    cat /sys/class/udc/a600000.usb/is_selfpowered
    cat /sys/class/udc/a600000.usb/is_a_peripheral
    cat /sys/kernel/config/usb_gadget/samurai/configs/c.1/MaxPower
    cat /sys/kernel/config/usb_gadget/samurai/configs/c.1/bmAttributes
    ls -l /sys/class/typec /sys/class/usb_role
} >"$prefix-usb-state.txt"
set +e
/tmp/k86-read-mp2650-input /dev/i2c-2 >"$prefix-refusal.txt" 2>&1
refusal=$?
set -e
echo "reader_exit=$refusal" >>"$prefix-refusal.txt"
[ "$refusal" = 2 ]
result=0
for sample in 1 2; do
    set +e
    /tmp/k86-read-mp2650-input /dev/i2c-0 >"$prefix-sample$sample.txt" 2>&1
    reader=$?
    set -e
    echo "reader_exit=$reader" >>"$prefix-sample$sample.txt"
    if [ "$reader" != 0 ]; then result=$reader; break; fi
    if [ "$sample" = 1 ]; then sleep 5; fi
done
/tmp/k84-read-mp2650 /dev/i2c-0 >"$prefix-after-registers.txt"
state >"$prefix-after-state.txt"
dmesg >"$prefix-after-dmesg.txt"
sha256sum "$prefix"-*.txt >"$prefix-hashes.txt"
tar -cf "$prefix.tar" "$prefix"-*.txt
gzip -c "$prefix.tar" >"$prefix.tar.gz"
cat "$prefix"-sample*.txt
cat "$prefix-after-state.txt"
cat "$prefix-usb-state.txt"
sha256sum "$prefix.tar" "$prefix.tar.gz"
exit "$result"
